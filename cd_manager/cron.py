import logging
from pyalpm import vercmp
from cd_manager.models import Package
from cd_manager.alpm import ALPMHelper


logger = logging.getLogger(__name__)


def check_for_new_pkgversions():
    logger.info("Start checking for new pkg versions in all repos.")
    try:
        for pkg in Package.objects.all():
            pkg.pkgbuild_repo_status_check()
            db_pkginfo = ALPMHelper().get_pkg_from_syncdbs(pkg.name)
            srcinfo = ALPMHelper.get_srcinfo(pkg.name).getcontent()
            # vercmp < 0 mean input 2 is higher, see man vercmp
            if vercmp(db_pkginfo.version, f"{srcinfo['pkgver']}-{srcinfo['pkgrel']}") < 0:
                pkg.build(repo_status_check=False)
    except BaseException:
        logger.exception("Cronjob checking for new pkg versions in all repos failed:")


def update_pacmandbs():
    logger.info("Updating pacman databases.")
    ALPMHelper().update_syncdbs()
