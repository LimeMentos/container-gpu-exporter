from pathlib import Path

from yaml import load, SafeLoader
from pydantic import BaseSettings


BASE_DIR = Path(__file__).parent


def load_configs():
    configs_file_path = Path(BASE_DIR / 'configs.yaml')
    if not configs_file_path.exists():
        raise Exception('The "configs.yaml" file is missing in the root directory')
    configs = load(open(configs_file_path, 'r'), Loader=SafeLoader)
    return configs


class Settings(BaseSettings):
    BASE_DIR: Path = BASE_DIR


settings = Settings()
configs = load_configs()