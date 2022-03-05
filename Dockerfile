FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./credentials.py /code/app/
COPY ./app /code/app
COPY ./gunicorn.sh /code

ENTRYPOINT ["./gunicorn.sh"]
