FROM python:3.10.8-buster
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
WORKDIR /workspace
COPY exporter.py exporter.py
COPY settings.py settings.py
COPY configs.yaml configs.yaml
CMD ["python", "exporter.py"]