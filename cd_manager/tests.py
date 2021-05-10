from django.test import TestCase
from cd_manager.models import Package
from cd_manager.alpm import ALPMHelper, PackageNotFoundError
from cd_manager.recursion_helper import Recursionlimit

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
            dep = Package.sanitize_dep(dep)
            get_deps(dep, level + 1, visited)


class TestRecursiveDeps(TestCase):

    # A ROS package with very minimal depencencies
    def test_ros_melodic_genmsg(self):
        get_deps("ros-melodic-genmsg")

    # A ROS package with a lot of dependencies
    def test_ros_melodic_desktop_full(self):
        get_deps("ros-melodic-desktop-full")
