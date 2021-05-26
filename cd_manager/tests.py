import sys
import os
import shutil
from django.test import TestCase, override_settings
from cd_manager.alpm import ALPMHelper, PackageNotFoundError
from cd_manager.recursion_helper import Recursionlimit
from cd_manager.models import Package

# Prototype implementation for Package.build() to check the visitor does the job


def get_deps(pkgname, level=0, visited=[]):
    if pkgname in visited:
        return
    visited.append(pkgname)
    try:
        deps = ALPMHelper().get_deps(pkgname=pkgname, rundeps=True, makedeps=True)
    except PackageNotFoundError as err:
        print(" " * level + str(err))
        return
    print(" " * level + pkgname + " has " + str(len(deps)) + " dependencies.")

    with Recursionlimit(2000):
        for dep in deps:
            dep = ALPMHelper.parse_dep_req(dep)
            get_deps(dep.name, level + 1, visited)


class TestALPMHelper(TestCase):

    def setUp(self):
        pkgs = ["gazebo-10", "ignition-transport", "ignition-transport-4", "sdformat", "sdformat-6"]
        for package in pkgs:
            Package.objects.create(name=package,
                                   repo_url=f"https://aur.archlinux.org/{package}.git",
                                   aur_push=False)

    # TODO: Rewrite tests to work without ROS packages in database
    # A ROS package with very minimal depencencies
    def test_ros_melodic_genmsg(self):
        get_deps("ros-melodic-genmsg")

    # A ROS package with a lot of dependencies
    def test_ros_melodic_desktop_full(self):
        get_deps("ros-melodic-desktop-full")

    @override_settings(PKGBUILDREPOS_PATH="./tests/pkgbuildrepos", PACMANREPO_PATH="./tests/repo")
    def test_versioned_dependencies(self):
        alpm = ALPMHelper()
        pkgs = list()
        deps = alpm.get_deps("gazebo-10")
        for wanted_dep in deps:
            wanted_dep = ALPMHelper.parse_dep_req(wanted_dep)
            query = Package.objects.filter(name__icontains=wanted_dep.name)
            if len(query) == 0:
                continue
            for potdep in query:
                if ALPMHelper.satifies_ver_req(wanted_dep, potdep.name):
                    pkgs.append(potdep.name)
                    break
        assert('sdformat-6' in pkgs)
        assert('ignition-transport-4' in pkgs)
        if os.path.isdir("./tests"):
            shutil.rmtree("./tests")
