#!/usr/bin/env bash

if [ ! -f /repo/abs_cd-local.db.tar.zst ]; then
    repo-add -q /repo/abs_cd-local.db.tar.zst
fi

python manage.py migrate
python manage.py crontab add

echo "Starting syslog:"
syslog-ng --no-caps
echo "Starting crond:"
crond -s

if ! grep -r -i -q "debug = true" data/settings.ini; then
    #Start with gunicorn
    python manage.py collectstatic --noinput
    gunicorn --bind :8000 --workers 3 abs_cd.wsgi:application
else
    echo "WARNING: DEBUG is set to TRUE! Don't use this in production";
    python manage.py runserver 0.0.0.0:8000
fi
