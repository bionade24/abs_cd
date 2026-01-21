import logging
import multiprocessing as mp
from datetime import timedelta
from django.contrib import admin
from django.http.response import HttpResponseRedirect
from django.urls import re_path
from django.utils import timezone
from django.shortcuts import render
from cd_manager.models import Package
from makepkg.docker_conn import Connection


logger = logging.getLogger(__name__)


class CustomAdminSite(admin.AdminSite):

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
                re_path(
                    r'^abs_cd_log$',
                    self.admin_view(self.show_abs_cd_log),
                    name='abs_cd_log',
                ),
                re_path(
                    r'^rebuild_all_pkgs$',
                    self.admin_view(self.rebuild_all_pkgs),
                    name='rebuild_all_pkgs',
                ),
        ]
        return custom_urls + urls

    def show_abs_cd_log(self, request, *args, **kwargs):
        request.current_app = self.name
        page = request.GET.get('page')
        LINES_PP = 500 # lines per page
        try:
            container = Connection().containers.list(filters={"label": "org.abs-cd=webcd_manager"})[0]
            full_log = container.logs().decode('utf-8').splitlines(keepends=True)
            page_count = 1 + len(full_log)//LINES_PP
            logger.debug(f"Requested page nr: {page} page count: {page_count}")
            try:
                page = int(page)
            except (ValueError, TypeError):
                logger.debug("Can't convert page nr {page} to int, assuming latest instead.")
                page = page_count
            if page >= page_count:
                text = full_log[-LINES_PP:]
                page = page_count
            elif isinstance(page, int) and page in range(1, page_count):
                lines_after = -LINES_PP*(page_count - page)
                lines_shown = lines_after - LINES_PP
                text = full_log[lines_shown:lines_after]
            else:
                raise RuntimeError(f"Page {page} can't be found.")
            text = "".join(text)
        except BaseException:
            logger.exception("Getting log from container failed:")
            text = None
            page_count = 1
            page = 1
        return render(request, 'admin/abs_cd_log.html',
                      context={'log': text, 'page': page, 'page_count': page_count,
                               'prev_page': page - 1 if page > 1 else None,
                               'next_page': page + 1 if page < page_count else None, })


    def rebuild_all_pkgs(self, request, *args, **kwargs):
        def rb_inner():
            request.current_app = self.name
            for pkg in Package.objects.all():
                if pkg.build_date < timezone.now() - timedelta(hours=12):
                    try:
                        pkg.rebuildtree()
                    except Exception as e:
                        logger.exception(f"Rebuild of package {pkg.name} failed:")
                else:
                    logger.debug(f"Package {pkg.name} has been built in the last 12 hours. Skipping rebuild despite force rbuild of all pkgs.")
        mp.Process(target=rb_inner).start()
        return HttpResponseRedirect('/cd_manager/overview/')



site = CustomAdminSite()


def get_site():
    return site
