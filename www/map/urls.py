from django.conf.urls import patterns, include, url
from map import views
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('map.views',
    url(r'^$', 'index'),
    url(
        r'^project/(?P<project_id>\d+)/deployment/(?P<dep_id>\d+)/download/$',
        'download_by_dep', name='download_by_dep'),
    url(
        r'^project/(?P<project_id>\d+)/deployment/(?P<dep_id>[0-9]+(\+[0-9]+)*)/$',
        'view_by_dep', name='view_by_dep'),
    #url(
    #    r'^project/(?P<project_id>\d+)/deployment/(?P<dep_id>\d+)/$',
    #    'view_by_dep', name='view_by_dep'),
    # url(r'^deployment/(?P<dep_id>\d+)/$', 'view_by_dep'),
    url(r'^target/(?P<target_id>\d+)/$', 'view_by_target'),
    url(r'^transmitter/(?P<tx_id>\d+)/$', 'view_by_tx'),
    url(r'^generic_graph', 'generic_graph', name='generic-graph'),
    url(r'^system_status', 'system_status', name='system-status'),
    url(r'^est_status', 'est_status', name='est-status'),

    url(
        r'^project/(?P<project_id>\d+)/deployment/([0-9]+(\+[0-9]+)*)/get_data/$',
        'get_data', name='get_data'),
)
