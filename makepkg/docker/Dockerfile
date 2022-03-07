FROM docker.io/archlinux/archlinux:latest
LABEL org.abs-cd.tools=makepkg
RUN pacman --noconfirm -Sy archlinux-keyring && pacman-key --init && pacman-key --populate archlinux
RUN systemd-machine-id-setup

RUN pacman --noconfirm -Syuq --needed base-devel devtools python
RUN useradd -m -d /build -s /bin/bash mkpkg
USER mkpkg
RUN gpg --list-keys
COPY gpg.conf /build/.gnupg/gpg.conf
USER root
COPY sudoers /etc/sudoers
COPY pacman.conf /etc/pacman.conf
COPY makepkg.conf /etc/makepkg.conf
WORKDIR /build
VOLUME "/src"
VOLUME "/repo"
COPY run.py /run.py
ENTRYPOINT ["/run.py"]
