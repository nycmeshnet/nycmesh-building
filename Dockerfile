FROM python:3.10.16-slim-bookworm

WORKDIR /usr/src/app

COPY building ./building/
COPY dashboard ./dashboard/
COPY manage.py ./
COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt
RUN python manage.py migrate

CMD [ "python", "manage.py", "runserver", "0.0.0.0:8080" ]
