import docker
import os
import glob
import subprocess
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from cd_manager.pkgbuild import SRCINFO
from abs_cd.confighelper import Confighelper


REPO_ADD_BIN = '/usr/bin/repo-add'
logger = logging.getLogger(__name__)


class PackageSystem:
    _docker_conn = None

    def __init__(self):
        if not PackageSystem._docker_conn:
            PackageSystem._docker_conn = docker.DockerClient(base_url=Confighelper()
                                                             .get_setting('DOCKER_SOCKET',
                                                                          'unix:///var/run/docker.sock'),
                                                             version='auto', tls=False)
        else:
            logger.debug("Connection to Docker socket already established")

        ######
        def generate_image():
            logger.info("Generating new image abs-cd/makepkg, please wait")
            PackageSystem._docker_conn.images.build(
                tag='abs-cd/makepkg', path=os.path.join(os.getcwd(), 'makepkg/docker'), rm=True, pull=True)
        ######
        try:
            one_week_ago = timezone.now() - timedelta(days=7)
            image = PackageSystem._docker_conn.images.get('abs-cd/makepkg')
            if datetime.utcfromtimestamp(image.history()[0]['Created']) < one_week_ago:
                generate_image()
        except docker.errors.ImageNotFound:
            generate_image()
        self._repo = PackageSystem._docker_conn.volumes.get(
            "abs_cd_local-repo")

    # pkgbase should be type cd_manager.models.Package()
    def build(self, pkgbase):
        packages = SRCINFO(os.path.join("/var/packages/", pkgbase.name, ".SRCINFO")).content['pkgname']
        if isinstance(packages, str):
            packages = [packages, ]
        output = None
        pkgbase.build_status = 'BUILDING'
        pkgbase.build_output = None
        pkgbase.save()
        try:
            output = PackageSystem \
                    ._docker_conn.containers.run(image='abs-cd/makepkg', remove=True,
                                                 mem_limit='8G', memswap_limit='8G', cpu_shares=128,
                                                 # TODO: Don't hardcode host paths
                                                 volumes={f'/var/local/abs_cd/packages/{pkgbase.name}':
                                                          {'bind': '/src', 'mode': 'ro'},
                                                          'abs_cd_local-repo':
                                                          {'bind': '/repo', 'mode': 'rw'}},
                                                 # Use microseconds as a fake UUID for container names to
                                                 # prevent name conflicts
                                                 name=f'mkpkg_{pkgbase.name}_{datetime.now().microsecond}')
            pkgbase.build_status = 'SUCCESS'
            pkg_paths = list()
            for pkg in packages:
                pkg_paths.extend(glob.glob(f"/repo/{pkg}-[0-9]*-[0-9]*-*.pkg.tar.*"))
            if len(pkg_paths) == 0:
                pkg_paths = glob.glob("/repo/*.pkg.tar.*")
            try:
                logger.warning(subprocess.run([REPO_ADD_BIN, '-q', '-R', 'abs_cd-local.db.tar.zst']
                                              + pkg_paths, check=True, stderr=subprocess.PIPE, cwd='/repo').
                               stderr.decode('UTF-8').strip('\n'))
            except subprocess.CalledProcessError as e:
                logger.error(e.stdout)
        except docker.errors.ContainerError as e:
            pkgbase.build_status = 'FAILURE'
            output = e.stderr
        finally:
            if output:
                pkgbase.build_output = output.decode('utf-8')
        pkgbase.build_date = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        pkgbase.save()
