from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class CdManagerConfig(AppConfig):
    name = 'cd_manager'


class Abs_cd_AdminSite(AdminConfig):
    default_site = 'cd_manager.admin_site.get_site'

