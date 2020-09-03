from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.views import generic

from .models import Package


def package(request, package_name):
    p = get_object_or_404(Package, name=package_name)
    return render(request, 'cd_manager/package.html',
     context={'package': p})


class PackageOverview(generic.ListView):
    model = Package
    context_object_name = 'package_list'
