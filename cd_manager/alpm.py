import pyalpm
import os
from dataclasses import dataclass
from typing import Callable
from typing import Optional
from pycman.config import PacmanConfig
from cd_manager.pkgbuild import SRCINFO
from django.conf import settings


@dataclass
class Dependency:
    name: str
    depends_entry: Optional[str]
    version: Optional[str]
    cmp_func: Optional[Callable[[int], bool]]


class ALPMHelper:
    _alpm_handle = None
    _syncdbs = None

    def __init__(self):
        if not ALPMHelper._alpm_handle:
            ALPMHelper._alpm_handle = PacmanConfig(
                conf='/etc/pacman.conf').initialize_alpm()
        if not ALPMHelper._syncdbs:
            ALPMHelper._syncdbs = ALPMHelper._alpm_handle.get_syncdbs()

    def update_syncdbs(self):
        for db in self._syncdbs:
            db.update(force=False)

    def get_pkg_from_syncdbs(self, pkgname: str):
        for db in self._syncdbs:
            pkg = db.get_pkg(pkgname)
            if isinstance(pkg, pyalpm.Package):
                return pkg
            else:
                pass
        raise PackageNotFoundError(pkgname)

    @staticmethod
    def get_srcinfo(pkgname: str):
        srcinfo_path = os.path.join(settings.PKGBUILDREPOS_PATH, pkgname, '.SRCINFO')
        if not os.path.isfile(srcinfo_path):
            from cd_manager.models import Package
            Package.objects.get(name=pkgname).pkgbuild_repo_status_check()
        return SRCINFO(srcinfo_path)

    def get_deps(self, pkgname, rundeps=True, makedeps=False, checkdeps=False):
        if not isinstance(pkgname, str):
            raise TypeError("Argument pkgname is not a String")
        deps = []
        srcinfo = ALPMHelper.get_srcinfo(pkgname)
        if srcinfo:
            if rundeps:
                deps += srcinfo.getrundeps()
            if makedeps:
                deps += srcinfo.getmakedeps()
            if checkdeps:
                deps += srcinfo.getcheckdeps()
        else:
            pkg = self.get_pkg_from_syncdbs(pkgname=pkgname)
            if rundeps:
                deps += pkg.depends
            if makedeps:
                deps += pkg.makedepends
            if checkdeps:
                deps += pkg.checkdepends
        return list(set(deps))

    @staticmethod
    def parse_dep_req(dep: str):
        # Yes it's better that way so it has a clear api at satifies_ver_req()
        seperators = (('>=', lambda x: True if x <= 0 else False),
                      ('<=', lambda x: True if x >= 0 else False),
                      ('=', lambda x: True if x == 0 else False),
                      ('>', lambda x: True if x < 0 else False),
                      ('<', lambda x: True if x > 0 else False))
        for sep in seperators:
            if sep[0] in dep:
                parts = dep.split(sep[0])
                return Dependency(parts[0], dep, parts[1], parts[1])
        return Dependency(dep, None, None, None)

    @staticmethod
    def satifies_ver_req(wanted_dep: Dependency, pot_dep: str):
        """Checks if pot_dep provides the wanted dep.
           pot_dep is expected to be in the CI database."""
        if not wanted_dep.version or not wanted_dep.cmp_func:
            return True
        pot_dep_provides = ALPMHelper.get_srcinfo(pot_dep).getcontent()['provides']
        if wanted_dep.depends_entry in pot_dep_provides:
            return True
        for entry in pot_dep_provides:
            pot_dep = ALPMHelper.parse_dep_req(entry)
            if wanted_dep.cmp_func(pyalpm.vercmp(wanted_dep.version, pot_dep.version)):
                return True
        return False


class PackageNotFoundError(RuntimeError):

    def __init__(self, pkgname):
        self.pkgname = pkgname

    def __str__(self):
        return f"{self.pkgname} not found in any given pacman database."
