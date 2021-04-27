FROM docker.io/archlinux/archlinux:latest
LABEL org.abs-cd=webcd_manager
RUN pacman --noconfirm -Sy archlinux-keyring && pacman-key --init && pacman-key --populate archlinux
RUN systemd-machine-id-setup

RUN pacman --noconfirm -Syuq --needed pyalpm openssh python-pip python-gitpython python-wheel cronie syslog-ng
RUN rm /etc/cron.d/0hourly #Disable anacron
COPY requirements.txt /root
RUN python3 -m pip install -r /root/requirements.txt
#Cronie can only log to syslog, so add a Docker fake tty as a log destination
RUN sed -i 's!{ file("/var/log/crond.log"); }!{ file("/var/log/crond.log"); file("/proc/1/fd/1"); }!g' /etc/syslog-ng/syslog-ng.conf
RUN mkdir /root/.ssh
COPY abs_cd/ /opt/abs_cd/abs_cd/
COPY cd_manager/ /opt/abs_cd/cd_manager/
COPY makepkg/ /opt/abs_cd/makepkg/
COPY static /opt/abs_cd/static/
COPY templates /opt/abs_cd/templates/
COPY manage.py /opt/abs_cd/
COPY settings.ini.template /opt/abs_cd/settings.ini.template
COPY pacman.conf /etc/pacman.conf
COPY config /root/.ssh
COPY known_hosts /root/.ssh
COPY startup.sh /opt/abs_cd
VOLUME /repo
VOLUME /var/packages
VOLUME /opt/abs_cd/data
VOLUME /opt/abs_cd/staticfiles
EXPOSE 8000
WORKDIR /opt/abs_cd

ENTRYPOINT ["bash", "startup.sh"]
