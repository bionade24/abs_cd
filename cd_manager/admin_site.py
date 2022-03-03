import logging
from django.contrib import admin
from django.conf.urls import url
from django.shortcuts import render
from makepkg.docker_conn import Connection

logger = logging.getLogger(__name__)


class CustomAdminSite(admin.AdminSite):

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
                url(
                    'abs_cd_log',
                    self.admin_view(self.show_abs_cd_log),
                    name='abs_cd_log',
                ),
        ]
        return custom_urls + urls

    def show_abs_cd_log(self, request, *args, **kwargs):
        request.current_app = self.name
        try:
            container = Connection().containers.list(filters={"label": "org.abs-cd=webcd_manager"})[0]
            log = container.logs().decode('utf-8')
        except BaseException:
            log = None
            logger.exception("Getting log from container failed.")
        return render(request, 'admin/abs_cd_log.html',
                      context={'log': log})


site = CustomAdminSite()


def get_site():
    return site
