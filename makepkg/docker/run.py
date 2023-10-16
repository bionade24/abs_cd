#!/usr/bin/env -S python -B

import argparse
import glob
import json
import os
import pwd
import subprocess
import shutil
import sys
import traceback
from subprocess import PIPE, STDOUT

USERNAME = 'builder'
USERDIR = '/builder'

build_log = ""


def chown_recursive(uid, gid, path):
    """
    Change all owner UIDs and GIDs of the files in the path to the given ones
    to not change either gid or uid, set that value to -1.
    From https://stackoverflow.com/questions/2853723
    Written by user "too much php"
    """
    os.chown(path, uid, gid)
    for root, dirs, files in os.walk(path):
        for momo in dirs:
            os.chown(os.path.join(root, momo), uid, gid)
        for file in files:
            os.chown(os.path.join(root, file), uid, gid)


def log(msg: str):
    global build_log
    build_log += (msg + "\n")


def print_and_exit(extcode: int, built_pkgs: list[str] | None = None) -> None:
    print(json.dumps({'exitcode': extcode, 'build_log': build_log, 'built_pkgs': built_pkgs}))
    sys.exit(extcode)


def main():
    """
    Main function for running this python script. Implements the argument parser, logic
    to build a complete package and copying of the build packages to the shared directory.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--execute',
        nargs='?',
        metavar='CMD',
        help=f"run CMD as {USERNAME} after the source directory was copied")
    parser.add_argument(
        '--sysupgrade',
        action='store_true',
        help="Run pacman -Syu before building")

    parser_args, makepkg_extra_flags = parser.parse_known_args()

    if not os.path.isfile("/src/PKGBUILD") or os.path.islink("/src/PKGBUILD"):
        log("No PKGBUILD file found! Aborting.")
        print_and_exit(2)

    src_folder = "/src"
    for entry in os.listdir(src_folder):
        srcpath = os.path.join(src_folder, entry)
        destpath = os.path.join(USERDIR, entry)
        if os.path.isdir(srcpath):
            shutil.copytree(srcpath, destpath, dirs_exist_ok=True)
        else:
            shutil.copy2(srcpath, destpath)

    userdata = pwd.getpwnam(USERNAME)
    chown_recursive(userdata.pw_uid, userdata.pw_gid, USERDIR)

    pacman_args = ['pacman', '--noconfirm', '-Sy']
    if parser_args.sysupgrade:
        pacman_args.append('-u')
    pacman_proc = subprocess.run(pacman_args, stdout=PIPE, stderr=STDOUT, encoding='UTF-8')
    if pacman_proc.returncode != 0:
        log("pacman exited with error:")
        log(pacman_proc.stdout)

    # if a command is specified with --execute, then run it
    if parser_args.execute:
        cmd = subprocess.run(['su', '-c', parser_args.execute, USERNAME], stdout=PIPE, stderr=STDOUT, encoding='UTF-8')
        if cmd.returncode != 0:
            log(cmd.stdout)
            log(f"Custom command \"{parser_args.execute}\" failed. Aborting.")
            print_and_exit(2)

    # If subprocess.Popen(user=uid) is used, gpg auto-key-retrieve doesn't work
    makepkg_args = ['su', '-c', "makepkg --force --syncdeps --noconfirm " +
                    " ".join(makepkg_extra_flags), USERNAME]
    makepkg_proc = subprocess.run(makepkg_args, stdout=PIPE, stderr=STDOUT, encoding='UTF-8')
    log(makepkg_proc.stdout)
    if makepkg_proc.returncode != 0:
        print_and_exit(1)

    built_packages = glob.glob(os.path.join(USERDIR, "*.pkg.tar.*"))
    if not built_packages:
        log("No packages were built!")
        print_and_exit(1)
    else:
        for file in built_packages:
            shutil.copy(file, "/repo")
        # Only get the filenames, not their full path
        print_and_exit(0, list(map(os.path.basename, built_packages)))


if __name__ == "__main__":
    try:
        main()
    # Use Exception not BaseException to not catch SystemExit
    except Exception:
        log(traceback.format_exc())
        print_and_exit(2)
