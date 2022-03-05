#! /bin/sh
exec gunicorn --chdir app main:app -w 2 --threads 1 -b 0.0.0.0:5000
