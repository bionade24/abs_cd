import pyalpm
import os
from cd_manager import pkgbuild
from pycman.config import PacmanConfig


class ALPMHelper:
    _alpm_handle = None
    _syncdbs = None

    def __init__(self):
        if not ALPMHelper._alpm_handle:
            ALPMHelper._alpm_handle = PacmanConfig(
                conf='/etc/pacman.conf').initialize_alpm()
        if not ALPMHelper._syncdbs:
            ALPMHelper._syncdbs = ALPMHelper._alpm_handle.get_syncdbs()

    def get_pkg_from_syncdbs(self, pkgname):
        if type(pkgname) != str:
            raise TypeError("Argument pkgname is not a String")
        for db in self._syncdbs:
            pkg = db.get_pkg(pkgname)
            if type(pkg) is pyalpm.Package:
                return pkg
            else:
                pass
        raise PackageNotFoundError(pkgname)

    def get_deps(self, pkgname, rundeps=True, makedeps=False, checkdeps=False):
        if type(pkgname) != str:
            raise TypeError("Argument pkgname is not a String")
        srcinfo_path = os.path.join('/var/packages', pkgname, '.SRCINFO')
        deps = []
        if os.path.isfile(srcinfo_path):
            srcinfo = pkgbuild.SRCINFO(srcinfo_path).content
            if rundeps:
                deps += srcinfo.get('depends')
            elif makedeps:
                deps += srcinfo.get('makedepends')
            elif checkdeps:
                deps += srcinfo.get('checkdepends')
        else:
            pkg = self.get_pkg_from_syncdbs(pkgname=pkgname)
            if rundeps:
                deps += pkg.depends
            elif makedeps:
                deps += pkg.makedepends
            elif checkdeps:
                deps += pkg.checkdepends
        return deps


class PackageNotFoundError(RuntimeError):

    def __init__(self, pkgname):
        self.pkgname = pkgname

    def __str__(self):
        return f"{self.pkgname} not found in any given pacman database."
