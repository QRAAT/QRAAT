from django.conf.urls import patterns, include, url
from qraat_ui import views
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('qraat_ui.views',
    url(r'^$', 'index'),
    url(
        r'^project/(?P<project_id>\d+)/deployment/(?P<dep_id>\d+)/$',
        'view_by_dep', name='view_by_dep'),
    # url(r'^deployment/(?P<dep_id>\d+)/$', 'view_by_dep'),
    url(r'^target/(?P<target_id>\d+)/$', 'view_by_target'),
    url(r'^transmitter/(?P<tx_id>\d+)/$', 'view_by_tx')
)
urlpatterns += patterns('',
  url(r'^admin/', include(admin.site.urls)),
)
