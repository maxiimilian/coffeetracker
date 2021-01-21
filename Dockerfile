FROM tiangolo/uwsgi-nginx-flask:python3.8

COPY ./src /app
RUN cd /app && pip install -r requirements.txt