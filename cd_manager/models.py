import os
import shutil
from cd_manager.alpm import ALPMHelper
from cd_manager.recursion_helper import Recursionlimit
from abs_cd import settings
from django.db import models
from makepkg.makepkg import PackageSystem
from django.utils import timezone
from datetime import timedelta
from git import Repo
from git.exc import GitCommandError


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
    aur_push_output = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    def repo_status_check(self):
        #Returns True if repo changed
        package_src = os.path.join('/var/packages', self.name)
        if not os.path.exists(package_src):
            Repo.clone_from(self.repo_url, package_src)
            return True
        else:
            def redownload():
                shutil.rmtree(package_src)
                return self.repo_status_check()

            try:
                repo = Repo(path=package_src)
                assert not repo.bare
                remote = repo.remote("origin")
                assert remote.exists()
                matched_url = None
                for url in remote.urls:
                    if url == self.repo_url:
                        matched_url = url
                assert matched_url
                head_before = repo.head.object.hexsha
                remote.pull()
                if head_before != repo.head.object.hexsha:
                    return True
            except AssertionError:
                return redownload()
            except GitCommandError as e:
                print(package_src + "\n" + e.stderr)
                return redownload()
        return False


    def run_cd(self):
        self.repo_status_check()
        PackageSystem().build(self)
        if self.build_status == 'SUCCESS' and self.aur_push:
            self.push_to_aur()
        else:
            if not self.aur_push and self.aur_push_output:
                self.aur_push_output = None
                self.save()

    @staticmethod
    def sanitize_dep(dep):
        # TODO: Proper version checking
        if '>=' in dep:
            dep = dep.split('>=')[0]
        elif '<=' in dep:
            dep = dep.split('<=')[0]
        elif '=' in dep:
            dep = dep.split('=')[0]
        return dep

    def build(self, force_rebuild=False, built_packages=[], repo_status_check=True):
        # As the dependency graph is not necessarily acyclic we have to make sure to check each node
        # only once. Otherwise this might end up in an endless loop (meaning we will hit the
        # recursion limit)
        if self.name in built_packages:
            return built_packages
        built_packages.append(self.name)

        if repo_status_check:
            self.repo_status_check()
        deps = ALPMHelper().get_deps(pkgname=self.name, rundeps=True, makedeps=True)
        with Recursionlimit(2000):
            for dep in deps:
                dep = self.sanitize_dep(dep)
                try:
                    dep_pkgobj = Package.objects.get(name=dep)
                    one_week_ago = timezone.now() - timedelta(days=7)
                    if dep_pkgobj.build_status != 'SUCCESS' or \
                       dep_pkgobj.build_date < one_week_ago or \
                       force_rebuild:
                        built_packages = dep_pkgobj.build(force_rebuild=force_rebuild, built_packages=built_packages)
                    else:
                        print(
                            f"Successful build of dependency {dep_pkgobj.name} is newer than 7 days. Skipping rebuild.")
                except Package.DoesNotExist:
                    pass
        self.run_cd()
        return built_packages

    def rebuildtree(self, built_packages=[]):
        self.build(force_rebuild=True, built_packages=built_packages)

    def push_to_aur(self):
        path = os.path.join(
            '/var/packages', self.name)
        try:
            pkg_repo = Repo(path=path).remote(name='aur')
        except ValueError:
            pkg_repo = Repo(path=path).create_remote(
                'aur', "aur@aur.archlinux.org:/{0}.git".format(self.name))
        pkg_repo.fetch()
        try:
            info = pkg_repo.push()[0]
            self.aur_push_output = str(info.summary)
        except GitCommandError as e:
            print(self.name + " has AUR push problems: ")
            self.aur_push_output = str(e)
        finally:
            self.save()

