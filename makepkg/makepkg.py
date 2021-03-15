import docker
import os
import glob
import subprocess
import sys
import logging
from wcmatch import wcmatch
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
            PackageSystem._docker_conn = docker.DockerClient(base_url=Confighelper().get_setting('DOCKER_SOCKET',
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
        if type(packages) == str:
            packages = [packages, ]
        old_pkgs = list()
        for pkg in packages:
            old_pkgs.extend(wcmatch.WcMatch('/repo', f"{pkg}-?.*-*-*.pkg.tar.*|{pkg}-?:?.*-*-*.pkg.tar.*" ).match())
        output = None
        pkgbase.build_status = 'BUILDING'
        pkgbase.build_output = None
        pkgbase.save()
        try:
            output = PackageSystem._docker_conn.containers.run(image='abs-cd/makepkg', remove=True,
                                                               # TODO: Don't hardcode host paths
                                                               mem_limit='8G', memswap_limit='8G', cpu_shares=128, volumes={f'/var/local/abs_cd/packages/{pkgbase.name}':
                                                                                                                            {'bind': '/src', 'mode': 'ro'}, 'abs_cd_local-repo': {'bind': '/repo', 'mode': 'rw'}},
            #Use microseconds as a fake UUID for container names to prevent name conflicts
                                                               name=f'mkpkg_{pkgbase.name}_{datetime.now().microsecond}')
            pkgbase.build_status = 'SUCCESS'
            new_pkgs = list()
            for pkg in packages:
                new_pkgs.extend(wcmatch.WcMatch('/repo', f"{pkg}-?.*-*-*.pkg.tar.*|{pkg}-?:?.*-*-*.pkg.tar.*" ).match())
            for pkglist in (old_pkgs, new_pkgs):
                pkglist.sort()
                pkglist.reverse()
            #Delete old pkgbases only if  build succeeds and they're new versions
            #TODO: Find a better solution that is still proof for multiple packages as output and works also if the packages haven't got removed during the run before.
            for (opath, npath) in zip(old_pkgs, new_pkgs):
                if opath != npath:
                    os.remove(opath)
                    new_pkgs.remove(opath)
            if len(new_pkgs) == 0:
                new_pkgs = glob.glob(
                    f"/repo/*.pkg.tar.*")
            try:
                logger.warning(subprocess.run([REPO_ADD_BIN, '-q', 'abs_cd-local.db.tar.zst']
                                              + new_pkgs, check=True, stderr=subprocess.PIPE, cwd='/repo').stderr.decode('UTF-8').strip('\n'))
            except subprocess.CalledProcessError as e:
                logger.error(e.stdout)
        except docker.errors.ContainerError as e:
            pkgbase.build_status = 'FAILURE'
            output = e.stderr
        finally:
            if not output is None:
                pkgbase.build_output = output.decode('utf-8')
        pkgbase.build_date = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        pkgbase.save()

