from django.conf.urls import patterns, include, url
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from django.views.i18n import javascript_catalog

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^map/', include('map.urls', namespace="map")),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^account/', include('account.urls', namespace="account")),
    url(r'^graphs/', include('graph.urls', namespace="graph")),
    url(r'^jsi18n/$', javascript_catalog),
    url(r'^$', 'project.views.index', name="index"),
    url(r'^project/', include('project.urls', namespace="project")),
    url(r'^data', 'project.views.render_data', name="get-data"),
)
