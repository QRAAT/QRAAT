from django.conf.urls import patterns, include, url
from qraat_ui import views
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('qraat_ui.views',
    url(r'^$', 'index'),
    url(r'^deployment/(?P<depID>\d+)/$', 'view_by_dep_id')
)
urlpatterns += patterns('',
  url(r'^admin/', include(admin.site.urls)),
)
