from django.urls import path
from . import views
from django.views.generic import RedirectView

app_name = 'polls'
urlpatterns = [
    path('overview/', views.PackageOverview.as_view(), name='overview'),
    path('<package_name>', views.package, name='package'),
    path('', RedirectView.as_view(url='overview/', permanent=True))
]
