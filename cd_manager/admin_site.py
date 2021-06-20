from django.contrib import admin
from django.conf.urls import url
from django.shortcuts import render
from makepkg.docker_conn import Connection


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
            # TODO: don't hardcode
            log = Connection().containers.get('abs_cd_abs_cd_1').logs().decode('utf-8')
        except BaseException:
            log = None
        return render(request, 'admin/abs_cd_log.html',
                      context={'log': log})


site = CustomAdminSite()


def get_site():
    return site
