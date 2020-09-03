FROM archlinux/base:latest
LABEL org.abs-cd=webcd_manager
RUN pacman --noconfirm -Sy archlinux-keyring && pacman-key --init && pacman-key --populate archlinux
RUN systemd-machine-id-setup

RUN pacman --noconfirm -Syuq --needed python-django python-docker pyalpm python-gitpython gunicorn
RUN useradd -m -d /opt/abs_cd -s /bin/sh abs_cd
COPY abs_cd/ /opt/abs_cd/abs_cd/
COPY cd_manager/ /opt/abs_cd/cd_manager/
COPY makepkg/ /opt/abs_cd/makepkg/
COPY manage.py /opt/abs_cd/
COPY pacman.conf /etc/pacman.conf
COPY startup.sh /opt/abs_cd
VOLUME /repo
VOLUME /var/packages
VOLUME /opt/abs_cd/data
VOLUME /opt/abs_cd/staticfiles
EXPOSE 8000
WORKDIR /opt/abs_cd

ENTRYPOINT ["bash", "startup.sh"]
