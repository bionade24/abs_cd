#!/usr/bin/env bash

if [ ! -f /repo/localhost.db.tar.zst ]; then
    repo-add -n /repo/localhost.db.tar.zst;
fi

python manage.py makemigrations
python manage.py migrate

if ! grep -r "DEBUG = True"; then
    #Start with gunicorn
    python manage.py collectstatic
    gunicorn --bind :8000 --workers 3 abs_cd.wsgi:application
    else
    echo "WARNING: DEBUG is set to TRUE! Don't use this in production";
    python manage.py runserver 0.0.0.0:8000
fi
