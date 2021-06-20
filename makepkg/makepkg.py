import docker
import os
import glob
import subprocess
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from cd_manager.alpm import ALPMHelper
from .docker_conn import Connection


REPO_ADD_BIN = '/usr/bin/repo-add'
logger = logging.getLogger(__name__)


class PackageSystem:

    def __init__(self):

        def generate_image():
            logger.info("Generating new image abs-cd/makepkg, please wait")
            Connection().images.build(
                tag='abs-cd/makepkg', path=os.path.join(os.getcwd(), 'makepkg/docker'), rm=True, pull=True)
        ######
        try:
            one_week_ago = timezone.now() - timedelta(days=7)
            image = PackageSystem.Connection().images.get('abs-cd/makepkg')
            if datetime.utcfromtimestamp(image.history()[0]['Created']) < one_week_ago:
                generate_image()
        except docker.errors.ImageNotFound:
            generate_image()
        self._repo = PackageSystem.Connection().volumes.get(
            "abs_cd_local-repo")

    # pkgbase should be type cd_manager.models.Package()
    def build(self, pkgbase):
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
            container_output = PackageSystem \
                .Connection().containers.run(image='abs-cd/makepkg', remove=False,
                                             mem_limit='8G', memswap_limit='8G', cpu_shares=128,
                                             # TODO: Don't hardcode host paths
                                             volumes={f'/var/local/abs_cd/packages/{pkgbase.name}':
                                                      {'bind': '/src', 'mode': 'ro'},
                                                      'abs_cd_local-repo':
                                                      {'bind': settings.PACMANREPO_PATH, 'mode': 'rw'},
                                                      '/var/cache/pacman/pkg':
                                                      {'bind': '/var/cache/pacman/pkg', 'mode': 'rw'},
                                                      },
                                             name=container_name)
            pkgbase.build_status = 'SUCCESS'
            new_pkgs = list()
            for pkg in packages:
                new_pkgs.extend(glob.glob(os.path.join(settings.PACMANREPO_PATH, f"{pkg}-[0-9]*-[0-9]*-*.pkg.tar.*")))
            if len(old_pkgs) == 0 and len(new_pkgs) == 0:
                pkg_paths = glob.glob(os.path.join(settings.PACMANREPO_PATH, "*.pkg.tar.*"))
            else:
                pkg_paths = list(set(new_pkgs) - set(old_pkgs))
            if len(pkg_paths) == 0:
                pkg_paths = new_pkgs
            try:
                repo_add_output = subprocess.run([REPO_ADD_BIN, '-q', '-R', 'abs_cd-local.db.tar.zst']
                                                 + pkg_paths, check=True, stderr=subprocess.PIPE, cwd='/repo') \
                                                 .stderr.decode('UTF-8').strip('\n')
                if repo_add_output:
                    logger.warning(repo_add_output)
            except subprocess.CalledProcessError as e:
                logger.error(e.stdout)
        except docker.errors.ContainerError as e:
            pkgbase.build_status = 'FAILURE'
            container_output = e.container.logs()
        finally:
            self.Connection().containers.get(container_name).remove()
            if container_output:
                pkgbase.build_output = container_output.decode('utf-8')
        pkgbase.build_date = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        pkgbase.save()
