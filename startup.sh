#!/usr/bin/env bash

if [ ! -f data/settings.ini ]; then
    echo "settings.ini did not exist, copyingfrom settings.ini.template"
    cp settings.ini.template data/settings.ini || { echo "settings.ini.template missing."; exit 1; }
fi

source <(grep pacmanrepo_name data/settings.ini | tr -d ' ')
export pacmanrepo_name

[ -f pacman.conf.tmpl ] || { echo 'pacman.conf.tmpl is missing.'; exit 1; }
envsubst '$pacmanrepo_name' < pacman.conf.tmpl > /etc/pacman.conf
[ -f makepkg/docker/pacman.conf.tmpl ] || { echo 'makepkg/docker/pacman.conf.tmpl is missing.'; exit 1; }
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
