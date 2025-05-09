FROM python:3.10-slim-bookworm

RUN pip install opcua numpy pandas openpyxl

COPY ./server.py /app/server.py
COPY ./machine-data.csv /app/machine-data.csv

WORKDIR /app
CMD ["python", "server.py"]