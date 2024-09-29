ABS-CD - CI/CD for the Arch Build System
==

Simple CI/CD for Arch Linux packages with optional support to push successfull built `PKGBUILD` repos to the AUR, written in Python with Django and Docker. 
Packages get built in clean Docker containers, afterwards the resulting packages get added to the local repo for the CI/CD, so other packages can depend on it.
Tested with > 300 AUR packages that I had been maintaining in the past.

Installation:
=

Preperations: Docker and a webserver with reverse proxying capabilities, e. g. nginx  
  
```
git clone --branch <latest version number> --depth=1 https://github.com/bionade24/abs_cd.git
cd abs_cd
docker-compose build --no-cache
docker-compose up -d
```
Config webserver to proxy gunicorn and serve static files, defaultly under `/srv/abs_cd/staticfiles` ([nginx example config](https://gist.github.com/bionade24/966001987ba718557cd0fcc64924938f))  
  
Config:
=

Per default, the config and data is stored under `/var/local/abs_cd/`.  
The most relevant config options can be configure in `settings.ini`, which automatically gets copied from `settings.ini.template` and filled out if not manually provided.  
Behaves like any Django App, so the [Django documentation](https://docs.djangoproject.com/en/5.1/) will help you with most things. (e.g. django settings.py is under abs_cd/abs_cd/settings.py and call `python manage.py createsuperuser` in the container to create admin user)  
The cronjob checking for updated repos is in the settings.py, too.  
Set `DEBUG=True` in `data/settings.ini` to allow django serving static files for development purposes.  
  
Optionally, a private ssh key for pushing/morring the PKGBUILD git repos of selected pkgs to the AUR on successfull builds, can be provided in the `data/` folder.  
Podman: Mount the podman socket instead, you can also manipulate the socket URL in the django container under `data/settings.ini`. Currently, the dev version of podman-compose is necessary. An example compose yaml for rootless mode can be found here: https://github.com/bionade24/abs_cd/issues/7#issuecomment-753252831  
  
Access repo/packages:
=
1. Either mount `abs_cd_local-repo` in a second container. Please be aware that then your pacman.conf repo name has to be changed from `abs_cd_local-repo` to your own in `settings.ini`. You can provide a unencrypted gpg key for signing packages and the repo database in the webinterface. If you don't do that, please be sure to provide your repo only over https to ensure data integrity.  
2. Copy them: `docker cp abs_cd:/repo PATH && rm PATH/repo/abs_cd-local.*`. For creating a repo with this approach, I recommend you to use [repo-add_and_sign](https://aur.archlinux.org/packages/repo-add_and_sign).  

Contributing & Bugreporting:
=
Before reporting anything, please check if what you want is already listed on the [projects board](https://github.com/users/bionade24/projects/2). The project currently is more in maintanance mode than anything else, as I personally lack the interest to further develop it. If you have any problems setting it up or using it, consider opening a thread in GH discussion or write me an email if you prefer so.  
