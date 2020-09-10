import docker
import os
import glob
import subprocess
from datetime import datetime
import sys


REPO_ADD_BIN = '/usr/bin/repo-add'


class PackageSystem:
    _docker_conn = None

    def __init__(self):
        if not PackageSystem._docker_conn:
            PackageSystem._docker_conn = docker.DockerClient(base_url='unix://var/run/docker.sock',
                                                             version='auto', tls=False)
        else:
            print("Connection already established")
        try:
            PackageSystem._docker_conn.images.get('abs-cd/makepkg')
        except docker.errors.ImageNotFound:
            path = os.path.join(os.getcwd(), 'cd_manager/makepkg/docker')
            PackageSystem._docker_conn.images.build(
                tag='abs-cd/makepkg', path=os.path.join(os.getcwd(), 'makepkg/docker'))
        self._repo = PackageSystem._docker_conn.volumes.get(
            "abs_cd_local-repo")

    # package should be type cd_manager.models.Package()
    def build(self, package):
        output = None
        try:
            output = PackageSystem._docker_conn.containers.run(image='abs-cd/makepkg', remove=True,
                                                               # TODO: Don't hardcode host
                                                               mem_limit='8G', memswap_limit='8G', cpu_shares=128, volumes={f'/var/local/abs_cd/packages/{package.name}':
                                                                                                                            {'bind': '/src', 'mode': 'ro'}, 'abs_cd_local-repo': {'bind': '/repo', 'mode': 'rw'}},
                                                               name=f'mkpkg_{package.name}')
            package.build_status = 'SUCCESS'
            new_pkgs = glob.glob(f"/repo/{package.name}-?.*-?-*.pkg.tar.*")
            if len(new_pkgs) == 0:
                new_pkgs = glob.iglob(f"/repo/{package.name}-?:?.*-?-*.pkg.tar.*")
            try:
                subprocess.run([REPO_ADD_BIN, '-R', '-q', 'abs_cd-local.db.tar.zst']
                               + new_pkgs, check=True, cwd='/repo')
            except subprocess.CalledProcessError as e:
                print(e.stdout, file=sys.stderr)
        except docker.errors.ContainerError as e:
            package.build_status = 'FAILURE'
            output = e.stderr
        finally:
            if not output is None:
                package.build_output = output.decode('utf-8')
        package.build_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        package.save()
