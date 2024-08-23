import logging
import os
from django.test import TestCase, override_settings
from cd_manager.alpm import ALPMHelper, PackageNotFoundError
from cd_manager.recursion_helper import Recursionlimit
from cd_manager.models import Package

# Prototype implementation for Package.build() to check the visitor does the job


def print_deps(pkgname, level=0, visited=None):
    if not visited:
        visited = []
    if pkgname in visited:
        return True
    visited.append(pkgname)
    try:
        deps = ALPMHelper().get_deps(pkgname=pkgname, rundeps=True, makedeps=True)
    except PackageNotFoundError as err:
        print(" " * level + str(err))
        return False
    print(" " * level + pkgname + " has " + str(len(deps)) + " dependencies.")

    with Recursionlimit(2000):
        for dep in deps:
            dep = ALPMHelper.parse_dep_req(dep)
            print_deps(dep.name, level + 1, visited)
    return True if len(deps) > 0 else False


@override_settings(PACMAN_CONFIG_PATH="./tests/pacman.conf")
class TestALPMHelper(TestCase):

    def setUp(self):
        if not os.path.exists("./tests/testroot/"):
            os.mkdir("./tests/testroot/")
        pkgs = ["gazebo-10", "ignition-transport", "ignition-transport-4", "sdformat", "sdformat-6",
                "seafile-client", "seafile", "nheko", "mtxclient",
                "lmdbxx"]
        for package in pkgs:
            Package.objects.create(name=package,
                                   # Git clone file://path/to/repo.bundle doesn't work
                                   repo_url=f"{os.getcwd()}/tests/pkgbuild_remote/{package}.bundle",
                                   aur_push=False)
        print(Package.objects.all())

    # A ROS package with very minimal depencencies
    @override_settings(PKGBUILDREPOS_PATH="./tests/pkgbuild_local", PACMANREPO_PATH="./tests/repo")
    def test_ros_melodic_genmsg(self):
        logging.disable(logging.INFO)
        assert print_deps("ros-melodic-genmsg")

    # A ROS package with a lot of dependencies
    @override_settings(PKGBUILDREPOS_PATH="./tests/pkgbuild_local", PACMANREPO_PATH="./tests/repo")
    def test_ros_melodic_desktop_full(self):
        logging.disable(logging.INFO)
        assert print_deps("ros-melodic-desktop-full")

    def test_for_falsely_found_deps(self):
        deps = (ALPMHelper().get_deps(pkgname="ros-build-tools-py3", rundeps=True, makedeps=True))
        assert len(deps) == 1
        assert "bash" in deps

    @override_settings(PKGBUILDREPOS_PATH="./tests/pkgbuild_local", PACMANREPO_PATH="./tests/repo")
    def test_versioned_dependencies(self):
        alpm = ALPMHelper()

        def figure_out_local_deps(pkgname):
            pkgs = list()
            wanted_deps = alpm.get_deps(pkgname, rundeps=True, makedeps=True)
            print(wanted_deps)
            for wanted_dep in wanted_deps:
                wanted_dep = ALPMHelper.parse_dep_req(wanted_dep)
                query = Package.objects.filter(name__icontains=wanted_dep.name)
                if len(query) == 0:
                    continue
                for potdep in query:
                    if ALPMHelper.satifies_ver_req(wanted_dep, potdep.name):
                        pkgs.append(potdep.name)
                        break
            return pkgs

        gazebo_deps = figure_out_local_deps("gazebo-10")
        assert 'sdformat-6' in gazebo_deps
        assert 'ignition-transport-4' in gazebo_deps
        assert 'sdformat' not in gazebo_deps
        assert 'ignition-transport' not in gazebo_deps

        seafile_client_deps = figure_out_local_deps("seafile-client")
        assert 'seafile' in seafile_client_deps

        nheko_deps = figure_out_local_deps("nheko")
        assert 'mtxclient' in nheko_deps
        assert 'lmdbxx' in nheko_deps

        #if os.path.isdir("./tests"):
        #    shutil.rmtree("./tests")
