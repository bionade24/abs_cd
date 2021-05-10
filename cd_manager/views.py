from django.shortcuts import get_object_or_404, render
from sortable_listview import SortableListView

from .models import Package


def package(request, package_name):
    p = get_object_or_404(Package, name=package_name)
    return render(request, 'cd_manager/package.html',
                  context={'package': p})


class PackageOverview(SortableListView):
    model = Package
    context_object_name = 'package_list'
    allowed_sort_fields = {'name': {'default_direction': '',
                                    'verbose_name': 'Package name'},
                           'build_status': {'default_direction': '',
                                            'verbose_name': 'Build status'},
                           'build_date': {'default_direction': '-',
                                          'verbose_name': 'Build date'}
                           }
    default_sort_field = 'name'
