#! /bin/sh
exec gunicorn --chdir app  -w 2 --threads 1 -b 0.0.0.0:5000 --certfile=/certs/ukrainehelp.emergenzehack.info.crt --keyfile=/certs/ukrainehelp.emergenzehack.info.key main:app
