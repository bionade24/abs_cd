#!/usr/bin/env bash

function enable () {
    [ -d ./tests/pkgbuild_remote ] || mkdir ./tests/pkgbuild_remote || exit 1
	[ -d ./tests/pacman_db ] || mkdir ./tests/pacman_db || exit 1
	sudo mount -t squashfs ./tests/pkgbuild_remote.squashfs ./tests/pkgbuild_remote || exit 1
	sudo mount -t squashfs ./tests/pacman_db.squashfs ./tests/pacman_db;
}

function disable () {
    sudo umount ./tests/pkgbuild_remote
    sudo umount ./tests/pacman_db;
}

function help () {
    echo "Usage: ./setup-testenv.sh	enable | disable | help";
}


case $1 in
    "enable")
        enable;
        ;;
    "disable")
        disable;
        ;;
    *)
        help;
esac
