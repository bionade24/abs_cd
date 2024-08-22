import os
import shutil
import logging
import glob
import subprocess
import gpg
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from cd_manager.alpm import ALPMHelper
from cd_manager.recursion_helper import Recursionlimit
from makepkg import makepkg
from datetime import timedelta, datetime
from git import Repo
from git.exc import GitCommandError


logger = logging.getLogger(__name__)

REPO_REMOVE_BIN = "/usr/bin/repo-remove"


class Package(models.Model):
    BuildStatus = models.TextChoices(
        'BuildStatus', 'SUCCESS FAILURE NOT_BUILT BUILDING PREPARING WAITING')
    name = models.CharField(max_length=100, primary_key=True)
    repo_url = models.CharField(max_length=100)
    makepkg_extra_args = models.CharField(max_length=255, blank=True)
    build_status = models.CharField(choices=BuildStatus.choices,
                                    default='NOT_BUILT', max_length=10)
    build_date = models.DateTimeField(null=True, blank=True)
    build_output = models.TextField(null=True, blank=True)
    aur_push = models.BooleanField(default=False)
    aur_push_output = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    def pkgbuild_repo_status_check(self):
        # Returns True if repo changed
        package_src = os.path.join(settings.PKGBUILDREPOS_PATH, self.name)
        if not os.path.exists(package_src):
            Repo.clone_from(self.repo_url, package_src)
            return True
        else:
            def redownload():
                shutil.rmtree(package_src)
                return self.pkgbuild_repo_status_check()

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
                logger.warning(package_src + "\n" + e.stderr)
                return redownload()
        return False

    def build(self, user: User = AnonymousUser, force_rebuild=False, scheduled_cd_pkgs=None, repo_status_check=True):
        # As the dependency graph is not necessarily acyclic we have to make sure to check each node
        # only once. Otherwise this might end up in an endless loop (meaning we will hit the
        # recursion limit)
        if not scheduled_cd_pkgs:
            scheduled_cd_pkgs = []
        if self.name in scheduled_cd_pkgs:
            return scheduled_cd_pkgs
        scheduled_cd_pkgs.append(self.name)

        self.build_status = 'PREPARING'
        self.build_output = None
        self.save()

        if repo_status_check:
            self.pkgbuild_repo_status_check()
        deps = ALPMHelper().get_deps(pkgname=self.name, rundeps=True, makedeps=True)
        with Recursionlimit(2000):
            for wanted_dep in deps:
                wanted_dep = ALPMHelper.parse_dep_req(wanted_dep)
                query = Package.objects.filter(name__icontains=wanted_dep.name)
                if len(query) == 0:
                    continue
                dep_pkgobj = None
                for potdep in query:
                    try:
                        potdep.pkgbuild_repo_status_check()  # For case only latest version of potdep satifies wanted_dep
                    except BaseException:  # TODO: Own exception system
                        logger.exception(f"Git operations for pkg {dep_pkgobj.name} providing dependency \
                                {wanted_dep.name} for pkg {self.name} failed:")
                        self.build_failure()
                    if ALPMHelper.satifies_ver_req(wanted_dep, potdep.name):
                        dep_pkgobj = potdep
                        logger.debug(f"{potdep.name} satifies dependency requirement {wanted_dep.depends_entry} \
                                       of {self.name}.")
                        break
                if not dep_pkgobj:
                    logger.debug(f"No package satisfiying {wanted_dep.depends_entry} in local database. \
                                   Trying next dependency of {self.name}")
                    continue
                one_week_ago = timezone.now() - timedelta(days=7)
                if dep_pkgobj.build_status != 'SUCCESS' or \
                   dep_pkgobj.build_date < one_week_ago or \
                   force_rebuild:
                    if self.build_status != 'WAITING':
                        self.build_status = 'WAITING'
                        self.save()
                    try:
                        scheduled_cd_pkgs = dep_pkgobj.build(user, force_rebuild=force_rebuild, scheduled_cd_pkgs=scheduled_cd_pkgs,
                                                      repo_status_check=False)
                    except BaseException:  # TODO: Own exception system
                        logger.exception(f"Building pkg {dep_pkgobj.name} providing dependency {wanted_dep.name} for pkg \
                                {self.name} failed:")
                        self.build_failure()
                else:
                    logger.info(
                        f"Successful build of dependency {dep_pkgobj.name} is newer than 7 days. Skipping rebuild.")

        if self.build_status != 'PREPARING':
            self.build_status = 'PREPARING'
            self.save()
        makepkg.PackageSystem().build(self, user, self.makepkg_extra_args)
        if self.build_status == 'SUCCESS' and self.aur_push:
            self.push_to_aur()
        elif not self.aur_push and self.aur_push_output:
            self.aur_push_output = None
            self.save()
        return scheduled_cd_pkgs

    def rebuildtree(self):
        self.build(force_rebuild=True)

    def build_failure(self):  # TODO: Enum for multiple failure types
        self.build_status = 'FAILURE'  # TODO: More appropriate new error type
        self.save()
        raise RuntimeError(f"Building {self.name} failed.")

    def push_to_aur(self):
        path = os.path.join(
            settings.PKGBUILDREPOS_PATH, self.name)
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
            logger.warning(self.name + " has AUR push problems: ")
            self.aur_push_output = str(e)
        finally:
            self.save()


@receiver(pre_delete, sender=Package)
def remove_pkgbuild_and_archpkg(sender, instance, using, **kwargs):
    package_src = os.path.join(settings.PKGBUILDREPOS_PATH, instance.name)
    if os.path.exists(package_src):
        srcinfo = ALPMHelper.get_srcinfo(instance.name).getcontent()
        packages = srcinfo['pkgname']
        pkg_version = srcinfo['pkgver'] + '-' + srcinfo['pkgrel']
        if 'epoch' in srcinfo:
            pkg_version = srcinfo['epoch'] + ':' + pkg_version
        logger.debug(f"Removing git repo of {instance.name}: {package_src}")
        shutil.rmtree(package_src)
    else:
        packages = [instance.name]
        pkg_version = None
    for pkg in packages:
        try:
            logger.debug(f"Trying to remove {pkg} from local repo database")
            repo_add_output = subprocess.run([REPO_REMOVE_BIN, '-q', '-R', settings.PACMANDB_FILENAME, pkg],
                                             stderr=subprocess.PIPE, cwd=settings.PACMANREPO_PATH) \
                                        .stderr.decode('UTF-8').strip('\n')
            if repo_add_output:
                logger.warning(repo_add_output)
        except subprocess.CalledProcessError as e:
            logger.warning(e.sdout + "\n This is itentional if the package was never built.")
        if pkg_version:
            for file in glob.iglob(f"/repo/{pkg}-{pkg_version}-*.pkg.tar.*"):
                logger.debug(f"Deleting {file}")
                os.remove(file)


class GpgKey(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    fingerprint = models.CharField(max_length=255, editable=False, unique=True)
    expiry_date = models.DateTimeField(null=True, blank=True, editable=False)
    label = models.CharField(max_length=255, unique=True)
    allow_sign_by_other_users = models.BooleanField(default=False)

    def __str__(self):
        return self.fingerprint

    @property
    def key(self):
        return "Try harder ;)"

    @key.setter
    def key(self, value):
        logger.debug("Attempting to import new GPG key.")
        ctx = gpg.Context(pinentry_mode=gpg.constants.PINENTRY_MODE_ERROR)
        result = ctx.key_import(value.encode('ASCII'))
        if result is not None and hasattr(result, "considered"):
            if not hasattr(result, "secret_imported") and len(result.imports) > 1:
                raise RuntimeError("Only one key per object is allowed.")
            logger.debug(f"Added GPG key {self.fingerprint} to keyring.")
            self.fingerprint = result.imports[0].fpr
            for sk in ctx.get_key(self.fingerprint).subkeys:
                if sk.can_sign:
                    if sk.expires == 0:
                        break
                    else:
                        sk_exp_date = datetime.utcfromtimestamp(sk.expires)
                        if not self.expiry_date or sk_exp_date > self.expiry_date:
                            self.expiry_date = sk_exp_date
            self.save()
        elif result is not None:
            raise RuntimeError("Importing GPG key failed: " + result)
        else:
            raise RuntimeError("Importing GPG key went horribly wrong, no result returned.")

    def sign(self, filepath):
        with open(filepath, 'rb') as file:
            content = file.read()
        with gpg.Context(pinentry_mode=gpg.constants.PINENTRY_MODE_ERROR) as ctx:
            key = ctx.get_key(self.fingerprint)
            ctx.signers = (key,)
            try:
                signature, result = ctx.sign(content, mode=gpg.constants.sig.mode.DETACH)
            except gpg.errors.GPGMEError as e:
                logger.exception(f"Signing {filepath} with {self.fingerprint} failed:")
                return
            logger.debug(f"GPG sign of {filepath}: {result}")
        with open(filepath + '.sig', 'wb') as sigfile:
            sigfile.write(signature)

    @staticmethod
    def get_most_appropriate_key(user: User):
        if not user == AnonymousUser:
            keys = GpgKey.objects.filter(owner=user).order_by('allow_sign_by_other_users')
            if len(keys) > 0:
                return keys[0]
        keys = GpgKey.objects.filter(allow_sign_by_other_users=True)
        return keys[0] if len(keys) > 0 else None


@receiver(pre_delete, sender=GpgKey)
def delete_key(sender, instance, using, **kwargs):
    if instance.fingerprint == "":
        return
    logger.debug(f"Attempting to delete GPG key {instance.fingerprint} from keyring.")
    with gpg.Context(pinentry_mode=gpg.constants.PINENTRY_MODE_ERROR) as ctx:
        key = ctx.get_key(instance.fingerprint)
        ctx.op_delete_ext(key, gpg.constants.DELETE_FORCE | gpg.constants.DELETE_ALLOW_SECRET)
