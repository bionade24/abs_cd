ABS-CD - CI/CD for the Arch Build System
==

Simple CI/CD for Arch Linux packages with optional support to push successfull built `PKGBUILD` repos to the AUR, written in Python with Django.

Installation:
=

```
git clone https://github.com/bionade24/abs_cd.git
docker-compose up --build -d
```
Per default, config and data is stored under `/var/local/abs_cd/`
