#! /bin/sh
exec gunicorn --chdir app  -w 2 --threads 1 -b 0.0.0.0:5000 --certfile=/certs/www.europehelp.info.crt --keyfile=/certs/www.europehelp.info.key main:app
