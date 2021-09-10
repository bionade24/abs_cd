FROM docker.io/archlinux/archlinux:latest
LABEL org.abs-cd.tools=makepkg
RUN pacman --noconfirm -Sy archlinux-keyring && pacman-key --init && pacman-key --populate archlinux
RUN systemd-machine-id-setup

RUN pacman --noconfirm -Syuq --needed base-devel devtools python
RUN useradd -m -d /build -s /bin/bash mkpkg
RUN su -c "gpg --list-keys" mkpkg
COPY sudoers /etc/sudoers
COPY pacman.conf /etc/pacman.conf
COPY makepkg.conf /etc/makepkg.conf
WORKDIR /build
VOLUME "/src"
VOLUME "/repo"
COPY run.py /run.py
ENTRYPOINT ["/run.py"]
