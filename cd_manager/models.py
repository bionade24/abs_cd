import os
from cd_manager.alpm import ALPMHelper
from django.db import models
from makepkg.makepkg import PackageSystem
from git import Repo


class Package(models.Model):
    BuildStatus = models.TextChoices(
        'BuildStatus', 'SUCCESS FAILURE NOT_BUILT BUILDING')
    name = models.CharField(max_length=100, primary_key=True)
    repo_url = models.CharField(max_length=100)
    build_status = models.CharField(choices=BuildStatus.choices,
                                    default='NOT_BUILT', max_length=10)
    build_date = models.DateTimeField(null=True, blank=True)
    build_output = models.TextField(null=True, blank=True)
    aur_push = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def cloned_repo_check(self):
        package_src = os.path.join('/var/packages', self.name)
        if not os.path.exists(package_src):
            Repo.clone_from(self.repo_url, package_src)

    def run_cd(self):
        self.cloned_repo_check()
        PackageSystem().build(self)
        if self.build_status is 'SUCCESS' and self.aur_push:
            self.push_to_aur()

    def rebuildtree(self, built_packages=[]):
        self.cloned_repo_check
        deps = ALPMHelper().get_deps(pkgname=self.name, rundeps=True, makedeps=True)
        for dep in deps:
            try:
                dep_pkgobj = Package.objects.get(name=dep)
                dep_pkgobj.rebuildtree(built_packages)
            except Package.DoesNotExist:
                pass
        if not self.name in built_packages:
            self.run_cd()
            built_packages.append(self.name)

    def push_to_aur(self):
        try:
            pkg_repo = Repo(path=os.path.join(
                '/var/packages', self.name)).remote(name='aur')
        except ValueError:
            pkg_repo = Repo(path=self.path).create_remote(
                'aur', "aur@aur.archlinux.org:/{0}.git".format(self.name))
        pkg_repo.fetch()
        try:
            pkg_repo.push()
        except BaseException as e:
            print(self.name + " has AUR push problems")
