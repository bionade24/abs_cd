FROM archlinux/base:latest
LABEL org.abs-cd.tools=makepkg
RUN pacman --noconfirm -Sy archlinux-keyring && pacman-key --init && pacman-key --populate archlinux
RUN systemd-machine-id-setup

RUN pacman --noconfirm -Syuq --needed base-devel python boost cmake
RUN useradd -m -d /build -s /bin/bash mkpkg
COPY sudoers /etc/sudoers
COPY pacman.conf /etc/pacman.conf
WORKDIR /build
VOLUME "/src"
VOLUME "/repo"
COPY run.py /run.py
ENTRYPOINT ["/run.py"]
