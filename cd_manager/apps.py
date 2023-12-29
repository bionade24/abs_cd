import sys
from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class CdManagerConfig(AppConfig):
    name = 'cd_manager'

    def ready(self):
        if "runserver" in sys.argv:
            from cd_manager.models import Package
            pkgs = Package.objects.filter(build_status="BUILDING").union(
            Package.objects.filter(build_status="PREPARIG"),
            Package.objects.filter(build_status="WAITING"))
            for pkg in pkgs:
                pkg.build_status = "NOT_BUILT"
                pkg.save()



class Abs_cd_AdminSite(AdminConfig):
    default_site = 'cd_manager.admin_site.get_site'

