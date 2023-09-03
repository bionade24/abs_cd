#!/usr/bin/env bash

if [ ! -f data/settings.ini ]; then
    cp settings.ini.template data/settings.ini
    echo "settings.ini did not exist, copied from settings.ini.template"
fi

source <(grep pacmanrepo_name data/settings.ini | tr -d ' ')
export pacmanrepo_name
envsubst '$pacmanrepo_name' < pacman.conf.tmpl > /etc/pacman.conf
envsubst '$pacmanrepo_name' < makepkg/docker/pacman.conf.tmpl > makepkg/docker/pacman.conf

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
