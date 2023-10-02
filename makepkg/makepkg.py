import docker
import os
import glob
import subprocess
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from cd_manager.alpm import ALPMHelper
from cd_manager import models
from .docker_conn import Connection


REPO_ADD_BIN = '/usr/bin/repo-add'
BUILDCONT_IMG = 'abs_cd/makepkg'
logger = logging.getLogger(__name__)


def get_pacmanrepo_host_path():
    if settings.PACMANREPO_HOST_PATH == 'Docker-volume':
        return Connection().volumes.list(filters={"label": "com.docker.compose.volume=local-repo"})[0].name
    else:
        return settings.PACMANREPO_HOST_PATH


class PackageSystem:

    def __init__(self):
        if settings.PACMANDB_FILENAME not in os.listdir(settings.PACMANREPO_PATH):
            # 1st run or repo name changed
            proc = subprocess.run([REPO_ADD_BIN, '-q', settings.PACMANDB_FILENAME],
                                  stderr=subprocess.PIPE, cwd=settings.PACMANREPO_PATH)
            if proc.returncode != 0:
                logger.error("Creating the pacman repo failed:\n" + proc.stderr)
            self._generate_image()
            return
        try:
            image = Connection().images.get(BUILDCONT_IMG)
        except docker.errors.ImageNotFound:
            self._generate_image()
            return
        one_week_ago = timezone.now() - timedelta(days=7)
        if datetime.utcfromtimestamp(image.history()[0]['Created']) < one_week_ago:
            self._generate_image()

    @staticmethod
    def _generate_image():
        logger.info(f"Generating new image of {BUILDCONT_IMG}, please wait")
        _, logs = Connection().images.build(
            tag=BUILDCONT_IMG, path=os.path.join(settings.ABS_CD_PROJECT_DIR, 'makepkg/docker'), rm=True, pull=True)
        kw = 'stream'
        logger.info("".join(map(lambda lobj: lobj[kw] if kw in lobj else '', logs)))

    # pkgbase should be type cd_manager.models.Package()
    def build(self, pkgbase, user, makepkg_args=""):
        packages = ALPMHelper.get_srcinfo(pkgbase.name).getcontent()['pkgname']
        container_output = None
        pkgbase.build_status = 'BUILDING'
        pkgbase.build_output = None
        pkgbase.save()
        try:
            old_pkgs = list()
            for pkg in packages:
                old_pkgs.extend(glob.glob(os.path.join(settings.PACMANREPO_PATH, f"{pkg}-[0-9]*-[0-9]*-*.pkg.tar.*")))
            # Use microseconds as a fake UUID for container names to
            # prevent name conflicts
            container_name = f'mkpkg_{pkgbase.name}_{datetime.now().microsecond}'
            container_output = \
                Connection().containers.run(image=BUILDCONT_IMG, command=(makepkg_args),
                                            remove=False, mem_limit='8G', memswap_limit='8G', cpu_shares=128,
                                            volumes={os.path.join(settings.PKGBUILDREPOS_HOST_PATH, pkgbase.name):
                                                     {'bind': '/src', 'mode': 'ro'},
                                                     get_pacmanrepo_host_path():
                                                     {'bind': settings.PACMANREPO_PATH, 'mode': 'rw'},
                                                     '/var/cache/pacman/pkg':
                                                     {'bind': '/var/cache/pacman/pkg', 'mode': 'rw'},
                                                     },
                                            name=container_name)
            pkgbase.build_status = 'SUCCESS'
            # TODO: Replace dumb comparison with built_pkgs from container output
            new_pkgs = list()
            for pkg in packages:
                new_pkgs.extend(glob.glob(os.path.join(settings.PACMANREPO_PATH, f"{pkg}-[0-9]*-[0-9]*-*.pkg.tar.zst")))
            if len(old_pkgs) == 0 and len(new_pkgs) == 0:
                pkg_paths = glob.glob(os.path.join(settings.PACMANREPO_PATH, "*.pkg.tar.zst"))
            else:
                pkg_paths = list(set(new_pkgs) - set(old_pkgs))
            if len(pkg_paths) == 0:
                pkg_paths = new_pkgs

            key = models.GpgKey.get_most_appropriate_key(user)
            if key:
                try:
                    for pkg_path in pkg_paths:
                        key.sign(pkg_path)
                except gpg.errors.GpgError:
                    logger.exception("Error while signing packages:")
            try:
                repo_add_output = subprocess.run([REPO_ADD_BIN, '-q', '-R', settings.PACMANDB_FILENAME]
                                                 + pkg_paths, check=True, stderr=subprocess.PIPE,
                                                 cwd=settings.PACMANREPO_PATH) \
                                                 .stderr.decode('UTF-8').strip('\n')
                if repo_add_output:
                    logger.warning(repo_add_output)
                if key:
                    try:
                        key.sign(os.path.join(settings.PACMANREPO_PATH, settings.PACMANDB_FILENAME))
                    except gpg.errors.GpgError:
                        logger.exception("Error while signing repo database:")
            except subprocess.CalledProcessError:
                logger.exception("Updating the repo database failed:")
        except docker.errors.ContainerError as e:
            pkgbase.build_status = 'FAILURE'
            container_output = e.container.logs()
        finally:
            Connection().containers.get(container_name).remove()
            if container_output:
                pkgbase.build_output = container_output.decode('utf-8')
        pkgbase.build_date = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        pkgbase.save()
