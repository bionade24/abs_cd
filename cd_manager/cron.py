import logging
import subprocess
from pyalpm import vercmp
from django.conf import settings
from cd_manager.models import Package
from cd_manager.alpm import ALPMHelper, PackageNotFoundError


logger = logging.getLogger(__name__)


def check_for_new_pkgversions():
    logger.info("Start checking for new pkg versions in all repos.")
    for pkg in Package.objects.all():
        try:
            pkg.pkgbuild_repo_status_check()
        except BaseException:
            logger.exception(f"Checking if repo of {pkg.name} is up-to-date failed:")
            continue
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
                continue  # Explicitness in code is good


def update_pacmandbs():
    logger.info("Updating pacman databases.")
    ALPMHelper().update_syncdbs()

def clean_pacman_cache():
    logger.info("Start cleaning pacman cache dir.")
    try:
        output = subprocess.run(['yes | /usr/bin/pacman -Sccq'], shell=True, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.PIPE, cwd=settings.PACMANREPO_PATH) \
                                    .stderr.decode('UTF-8').strip('\n')
        if output:
            logger.warning(output)
    except subprocess.CalledProcessError as e:
        logger.exception(e)
