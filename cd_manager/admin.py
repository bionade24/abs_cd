from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.conf.urls import url
from django.http.response import HttpResponseRedirect
from multiprocessing import Process
from cd_manager.models import Package
from cd_manager.admin_site import site


# Register your models here.


@admin.register(Package, site=site)
class PackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'build_status',
                    'build_date',
                    'package_actions')
    search_fields = ("name", )
    ordering = ('name', )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            url(
                r'^(?P<package_name>.+)/run_cd/$',
                self.admin_site.admin_view(self.run_cd),
                name='run_cd',
            ),
            url(
                r'^(?P<package_name>.+)/rebuildtree/$',
                self.admin_site.admin_view(self.rebuildtree),
                name='rebuildtree',
            ),
        ]
        return custom_urls + urls

    def package_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Build Package</a>&nbsp;'
            '<a class="button" href="{}">Rebuild Dep Tree</a>',
            reverse('admin:run_cd', args=[obj.pk]),
            reverse('admin:rebuildtree', args=[obj.pk]),
        )
    package_actions.short_description = 'Package Actions'
    package_actions.allow_tags = True

    def run_cd(self, request, package_name, *args, **kwargs):
        request.current_app = self.admin_site.name
        pkg = Package.objects.get(name=package_name)
        Process(target=pkg.build).start()
        return HttpResponseRedirect('/admin/cd_manager/package/?o=2.1')

    def rebuildtree(self, request, package_name, *args, **kwargs):
        request.current_app = self.admin_site.name
        pkg = Package.objects.get(name=package_name)
        Process(target=pkg.rebuildtree).start()
        return HttpResponseRedirect('/admin/cd_manager/package/?o=2.1')

