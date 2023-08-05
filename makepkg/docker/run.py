#! /bin/python3 -B

import argparse
import glob
import os
import os.path
import pwd
import subprocess
import shutil
import shlex
import sys

USERNAME = 'builder'
USERDIR = '/builder'


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
            try:
                os.chown(os.path.join(root, momo), uid, gid)
            except Exception as e:
                print(e, file=sys.stderr)
        for file in files:
            try:
                os.chown(os.path.join(root, file), uid, gid)
            except Exception as e:
                print(e, file=sys.stderr)


def main():
    """
    Main function for running this python script. Implements the argument parser, logic
    to build a complete package and copying of the build packages to the shared directory.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-e',
        '--execute',
        nargs='?',
        help="CMD to run the command after the source directory was copied")
    parser.add_argument(
        '-s',
        '--sysupgrade',
        action='store_true',
        help="Run pacman -Syu before building")

    parser_args, makepkg_extra_flags = parser.parse_known_args()

    if not os.path.isfile("/src/PKGBUILD") or os.path.islink("/src/PKGBUILD"):
        print("No PKGBUILD file found! Aborting.", file=sys.stderr)
        sys.exit(1)

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
    pacman_proc = subprocess.run(pacman_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if pacman_proc.returncode != 0:
        print(pacman_proc.stdout.decode('UTF-8'), file=sys.stderr)

    # if a command is specified in -e, then run it
    if parser_args.execute:
        subprocess.run(shlex.split(parser_args.execute))

    # If subprocess.Popen(user=uid) is used, gpg auto-key-retrieve doesn't work
    makepkg_args = ['su', '-c', "makepkg --force --syncdeps --noconfirm " +
                    " ".join(makepkg_extra_flags), USERNAME]
    if subprocess.Popen(makepkg_args).wait() != 0:
        sys.exit(2)

    built_packages = glob.iglob(os.path.join(USERDIR, "*.pkg.tar.*"))
    if not built_packages:
        print("No packages were built!", file=sys.stderr)
        sys.exit(2)
    else:
        for file in built_packages:
            shutil.copy(file, "/repo")
    sys.exit(0)


if __name__ == "__main__":
    main()
