ABS-CD - CI/CD for the Arch Build System
==

Simple CI/CD for Arch Linux packages with optional support to push successfull built `PKGBUILD` repos to the AUR, written in Python with Django and Docker. 
Packages get built in clean Docker containers, afterwards the resulting packages get added to the local repo for the CI/CD, so other packages can depend on it.
Tested with > 300 AUR packages I maintain.

Installation:
=

Preperations: Docker and a webserver with reverse proxying capabilities, e. g. nginx  
  
```
git clone https://github.com/bionade24/abs_cd.git
docker-compose up --build -d
```
Config webserver to proxy gunicorn and serve static files, defaultly under `/srv/abs_cd/staticfiles` ([nginx example config](https://gist.github.com/bionade24/966001987ba718557cd0fcc64924938f))  
(Optionally add private ssh key for aur push)  
  
Config:
=

Per default, config and data is stored under `/var/local/abs_cd/`.  
Behaves like any Django App, so the [Django documentation](https://docs.djangoproject.com/en/3.1/) will help you with most things.  
Set `DEBUG=True` in `data/settings.ini` to allow django serving static files.  
