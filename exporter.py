import logging
import time
from traceback import format_exc

from prometheus_client import start_http_server, Gauge
from pydantic import BaseModel
import docker
import pynvml

from settings import configs


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(threadName)s | %(lineno)d | %(funcName)s | %(message)s'
)


class ContainerGpuExporterConfig(BaseModel):
    exporter_port: int
    detecting_interval: int


class ContainerGpuExporter(object):
    def __init__(self, configs):
        self.logger = logging.getLogger('MAIN_THREAD')
        self.configs = configs
        self.docker_client = docker.from_env()
        pynvml.nvmlInit()
        self.detecting_loop()

    def __del__(self):
        pynvml.nvmlShutdown()

    def get_container_info(self):
        container_info = {}
        containers = self.docker_client.containers.list()
        for container in containers:
            container_info[container.attrs['State']['Pid']] = container.attrs['Name'][1:]
        return container_info

    @staticmethod
    def get_gpu_info():
        gpu_count = pynvml.nvmlDeviceGetCount()
        gpu_info = []
        for gpu_index in range(gpu_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)
            gpu_utilization_rates = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            compute_processes_info = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
            container_memory_usage = {}
            for process in compute_processes_info:
                container_memory_usage[process.pid] = process.usedGpuMemory / 1024 / 1024
            gpu_info.append({
                'index': gpu_index,
                'name': pynvml.nvmlDeviceGetName(handle).decode('utf-8'),
                'uuid': pynvml.nvmlDeviceGetUUID(handle).decode('utf-8'),
                'core_utilization': gpu_utilization_rates.gpu,
                'memory_utilization': gpu_utilization_rates.memory,
                'power_usage': pynvml.nvmlDeviceGetPowerUsage(handle) / 1000,
                'power_limit': pynvml.nvmlDeviceGetEnforcedPowerLimit(handle) / 1000,
                'memory_usage': gpu_memory_info.used / 1024 / 1024,
                'memory_total': gpu_memory_info.total / 1024 / 1024,
                'container_memory_usage': container_memory_usage
            })
        return gpu_info

    def detecting_loop(self):
        start_http_server(self.configs.exporter_port)
        logger = logging.getLogger('DETECT_LOOP')
        logger.info('Detect loop started.')
        gpu_core_utilization = Gauge('core_utilization', 'Core utilization of GPU', ['index', 'name', 'uuid'])
        gpu_memory_utilization = Gauge('memory_utilization', 'Memory utilization of GPU', ['index', 'name', 'uuid'])
        gpu_power_usage = Gauge('power_usage', 'Power usage of GPU', ['index', 'name', 'uuid'])
        gpu_power_limit = Gauge('power_limit', 'Power limit of GPU', ['index', 'name', 'uuid'])
        gpu_memory_usage = Gauge('memory_usage', 'Memory usage of GPU', ['index', 'name', 'uuid'])
        gpu_memory_total = Gauge('memory_total', 'Memory total of GPU', ['index', 'name', 'uuid'])
        container_gpu_memory_usage = Gauge('container_gpu_memory_usage', 'Usage of GPU memory on container level', ['index', 'name', 'uuid', 'container_name'])
        while True:
            try:
                gpu_info = self.get_gpu_info()
                container_info = self.get_container_info()
                for gpu in gpu_info:
                    gpu_core_utilization.labels(index=gpu['index'], uuid=gpu['uuid'], name=gpu['name']).set(gpu['core_utilization'])
                    gpu_memory_utilization.labels(index=gpu['index'], uuid=gpu['uuid'], name=gpu['name']).set(gpu['memory_utilization'])
                    gpu_power_usage.labels(index=gpu['index'], uuid=gpu['uuid'], name=gpu['name']).set(gpu['power_usage'])
                    gpu_power_limit.labels(index=gpu['index'], uuid=gpu['uuid'], name=gpu['name']).set(gpu['power_limit'])
                    gpu_memory_usage.labels(index=gpu['index'], uuid=gpu['uuid'], name=gpu['name']).set(gpu['memory_usage'])
                    gpu_memory_total.labels(index=gpu['index'], uuid=gpu['uuid'], name=gpu['name']).set(gpu['memory_total'])
                    for pid in gpu['container_memory_usage'].keys():
                        if pid in container_info:
                            container_name = container_info[pid]
                            container_gpu_memory_usage.labels(index=gpu['index'], uuid=gpu['uuid'], name=gpu['name'], container_name=container_name).set(gpu['container_memory_usage'][pid])
                        else:
                            gpu['container_info'].pop(pid)
                time.sleep(self.configs.detecting_interval)
            except Exception:
                logger.error(f'An exception occurred in detect loop\n{format_exc()}')
                time.sleep(1)


if __name__ == "__main__":
    container_gpu_exporter_configs = ContainerGpuExporterConfig(**configs['container_gpu_exporter'])
    ContainerGpuExporter(container_gpu_exporter_configs)
