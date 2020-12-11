import docker
import os
import glob
import subprocess
import sys
from wcmatch import wcmatch
from datetime import datetime, timedelta
from django.utils import timezone


REPO_ADD_BIN = '/usr/bin/repo-add'


class PackageSystem:
    _docker_conn = None

    def __init__(self):
        if not PackageSystem._docker_conn:
            PackageSystem._docker_conn = docker.DockerClient(base_url='unix://var/run/docker.sock',
                                                             version='auto', tls=False)
        else:
            print("Connection already established")
        ######
        def generate_image():
            PackageSystem._docker_conn.images.build(
                tag='abs-cd/makepkg', path=os.path.join(os.getcwd(), 'makepkg/docker'))
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

    # package should be type cd_manager.models.Package()
    def build(self, package):
        old_pkgs = wcmatch.WcMatch('/repo', f"{package.name}-?.*-*-*.pkg.tar.*|{package.name}-?:?.*-*-*.pkg.tar.*" ).match()
        output = None
        package.build_status = 'BUILDING'
        package.build_output = None
        package.save()
        try:
            output = PackageSystem._docker_conn.containers.run(image='abs-cd/makepkg', remove=True,
                                                               # TODO: Don't hardcode host
                                                               mem_limit='8G', memswap_limit='8G', cpu_shares=128, volumes={f'/var/local/abs_cd/packages/{package.name}':
                                                                                                                            {'bind': '/src', 'mode': 'ro'}, 'abs_cd_local-repo': {'bind': '/repo', 'mode': 'rw'}},
                                                               name=f'mkpkg_{package.name}')
            package.build_status = 'SUCCESS'
            new_pkgs = wcmatch.WcMatch('/repo', f"{package.name}-?.*-*-*.pkg.tar.*|{package.name}-?:?.*-*-*.pkg.tar.*" ).match()
            #Delete old packages only if  build succeeds and they're new versions
            for (opath, npath) in zip(old_pkgs, new_pkgs):
                if opath != npath:
                    os.remove(opath)
            if len(new_pkgs) == 0:
                new_pkgs = glob.glob(
                    f"/repo/*.pkg.tar.*")
            try:
                subprocess.run([REPO_ADD_BIN, '-q', 'abs_cd-local.db.tar.zst']
                               + new_pkgs, check=True, cwd='/repo')
            except subprocess.CalledProcessError as e:
                print(e.stdout, file=sys.stderr)
        except docker.errors.ContainerError as e:
            package.build_status = 'FAILURE'
            output = e.stderr
        finally:
            if not output is None:
                package.build_output = output.decode('utf-8')
        package.build_date = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        package.save()

