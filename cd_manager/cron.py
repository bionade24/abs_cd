import logging
from pyalpm import vercmp
from cd_manager.models import Package
from cd_manager.alpm import ALPMHelper, PackageNotFoundError
from django.conf import settings


logger = logging.getLogger(__name__)


def check_for_new_pkgversions():
    logger.info("Start checking for new pkg versions in all repos.")
    try:
        for pkg in Package.objects.all():
            pkg.pkgbuild_repo_status_check()
            try:
                db_pkginfo_version = ALPMHelper().get_pkg_from_syncdbs(pkg.name).version
            except PackageNotFoundError:
                db_pkginfo_version = '-1'
            srcinfo = ALPMHelper.get_srcinfo(pkg.name).getcontent()
            srcinfo_version = f"{srcinfo['pkgver']}-{srcinfo['pkgrel']}"
            # vercmp < 0 mean input 2 is higher, see man vercmp
            if vercmp(db_pkginfo_version, srcinfo_version) < 0:
                try:
                    pkg.build(repo_status_check=False)
                except BaseException:
                    logger.exception(f"An automatic build of package {pkg.name} was triggered but failed")
    except BaseException:
        logger.exception("Cronjob checking for new pkg versions in all repos failed:")


def update_pacmandbs():
    logger.info("Updating pacman databases.")
    ALPMHelper().update_syncdbs()
