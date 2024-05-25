from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.urls import re_path
from django.http.response import HttpResponseRedirect
from multiprocessing import Process
from cd_manager.models import Package, GpgKey
from cd_manager.forms import GpgKeySubmitForm
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
            re_path(
                r'^(?P<package_name>.+)/build/$',
                self.admin_site.admin_view(self.build),
                name='build',
            ),
            re_path(
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
            reverse('admin:build', args=[obj.pk]),
            reverse('admin:rebuildtree', args=[obj.pk]),
        )
    package_actions.short_description = 'Package Actions'
    package_actions.allow_tags = True

    def build(self, request, package_name, *args, **kwargs):
        request.current_app = self.admin_site.name
        pkg = Package.objects.get(name=package_name)
        Process(target=pkg.build, args=[request.user]).start()
        return HttpResponseRedirect('/admin/cd_manager/package/?o=2.1')

    def rebuildtree(self, request, package_name, *args, **kwargs):
        request.current_app = self.admin_site.name
        pkg = Package.objects.get(name=package_name)
        Process(target=pkg.rebuildtree).start()
        return HttpResponseRedirect('/admin/cd_manager/package/?o=2.1')


@admin.register(GpgKey, site=site)
class GpgKeyAdmin(admin.ModelAdmin):
    # If the GpgKeySubmitForm is changed, change add_fieldsets accordingly
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('owner', 'label', 'allow_sign_by_other_users', 'gpg_key',),
        }),
    )
    add_form = GpgKeySubmitForm
    readonly_fields = ('fingerprint', 'expiry_date')
    list_display = ('label', 'fingerprint')
    search_fields = ('label', 'fingerprint')
    ordering = ('label', 'fingerprint')

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """
        Use special form for creation. From django/contrib/auth/admin.py
        """
        defaults = {}
        if obj is None:
            defaults['form'] = self.add_form
        defaults.update(**kwargs)
        return super().get_form(request, obj, **defaults)

