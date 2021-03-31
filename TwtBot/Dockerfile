FROM python:3.7.2-alpine3.8

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /usr/src/app

RUN pip install --upgrade pip
COPY ./requirements.txt .
COPY ./config.json .
COPY ./main.py .

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "/usr/src/app/main.py"]