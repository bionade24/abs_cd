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


def eprint(*args, **kwargs):
    """
    Helper function for printing to sys.stderr
    """
    print(*args, file=sys.stderr, **kwargs)


class MakepkgContainer:
    """
    Class implementing a package builder for Arch Linux using Docker.
    This is the file running inside the container.
    """
    __restDefaults = "--force --syncdeps --noconfirm"

    def __init__(self):
        self.parser = None
        self.rest = None
        self.command = None
        self.group = None
        self.run_pacman_syu = None
        self.user = None

    @staticmethod
    def copy_tree(src, dst, symlinks=False, ignore=None):
        """
        Copy the directory tree from src to dst
        From https://stackoverflow.com/questions/1868714
        Written by user atzz
        """
        for item in os.listdir(src):
            source_directory = os.path.join(src, item)
            destination_directory = os.path.join(dst, item)
            if os.path.isdir(source_directory):
                shutil.copytree(source_directory,
                                destination_directory, symlinks, ignore)
            else:
                shutil.copy2(source_directory, destination_directory)

    @staticmethod
    def change_user_or_gid(uid, gid, path):
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
                    eprint(e)
            for file in files:
                try:
                    os.chown(os.path.join(root, file), uid, gid)
                except Exception as e:
                    eprint(e)

    # From https://www.tutorialspoint.com/How-to-change-the-permission-of-a-directory-using-Python
    # Written by Rajendra Dharmkar
    @staticmethod
    def change_permissions_recursively(path, mode):
        """
        Change the permissions of all files and directories in the given path to the given mode
        """
        os.chmod(path, mode)
        for root, dirs, files in os.walk(path, topdown=False):
            for directory in [os.path.join(root, d) for d in dirs]:
                os.chmod(directory, mode)
            for file in [os.path.join(root, f) for f in files]:
                os.chmod(file, mode)

    @staticmethod
    def append_to_file(path, content):
        """
        Append the given content to the file found in the given path
        """
        with open(path, "a+") as file:
            file.seek(0, 2)
            file.write(content)

    def main(self):
        """
        Main function for running this python script. Implements the argument parser, logic
        to build a complete package and copying of the build packages to the shared directory.
        """
        self.parser = argparse.ArgumentParser(prog="dmakepkgContainer")
        self.parser.add_argument(
            '-e',
            nargs='?',
            help="CMD to run the command after the source directory was copied")
        self.parser.add_argument(
            '-p',
            action='store_true',
            help="Run a pacman -Syu before building")

        namespace, self.rest = self.parser.parse_known_args()

        if not os.path.isfile("/src/PKGBUILD") or os.path.islink("/src/PKGBUILD"):
            eprint("No PKGBUILD file found! Aborting.")
            sys.exit(1)

        self.command = namespace.e
        self.run_pacman_syu = namespace.p
        build_user_uid = pwd.getpwnam("mkpkg").pw_uid
        build_user_gid = pwd.getpwnam("mkpkg").pw_gid
        self.copy_tree("/src/", "/build")
        self.change_user_or_gid(build_user_uid, build_user_gid, "/build")

        if self.run_pacman_syu:
            arguments = "pacman --noconfirm -Syu".split()
            pacman_process = subprocess.Popen(arguments)
            pacman_process.wait()
        else:
            arguments = "pacman --noconfirm -Sy".split()
            pacman_process = subprocess.Popen(arguments)
            pacman_process.wait()
        flags = None

        if not self.rest:
            flags = self.__restDefaults.split()
        else:
            # translate list object to space seperated arguments
            flags = self.rest

        # if a command is specified in -e, then run it
        if self.command:
            args = shlex.split(self.command)
            subprocess.run(args)

        arguments = ['su', '-c',
                     'makepkg {}'.format(" ".join(flags)),
                     '-s',
                     '/bin/bash',
                     '-l', 'mkpkg']
        makepkg_process = subprocess.Popen(arguments)
        while makepkg_process.poll() is None:
            outs, errs = makepkg_process.communicate(input="")
            if outs:
                print(outs)
            if errs:
                eprint(errs)

        built_packages = glob.glob("/build/.out/*")
        if not built_packages:
            eprint("No packages were built!")
            sys.exit(2)
        else:
            # copy any packages
            # use globbing to get all packages
            for item in built_packages:
                try:
                    shutil.copy(item, "/repo")
                except Exception as e:
                    eprint(e)
        sys.exit(0)


if __name__ == "__main__":
    MakepkgContainer().main()
