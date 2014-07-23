from django.conf.urls import patterns, include, url
import qraat_ui, qraat_auth
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from django.views.i18n import javascript_catalog 

admin.autodiscover()

    
project_patterns = patterns('qraatview.views',
    # url(r'^transmitters/$', 'transmitters'),

    # url(r'^transmitters/(?P<transmitter_id>\d+)/$',
    #     'get_transmitter'),

    url(r'^$', 'projects', name='projects'),

    url(r'^create-project/$',
        'create_project', name='create-project'),

    url(
        r'^(?P<project_id>\d+)/$', 'show_project',
        name='show-project'),

    url(
        r'^(?P<project_id>\d+)/transmitter/(?P<transmitter_id>\d+)/$',
        'show_transmitter',
        name='show-transmitter'),

    url(
        r'^(?P<project_id>\d+)/location/(?P<location_id>\d+)/$',
        'show_location',
        name='show-location'),

    url(
        r'^(?P<project_id>\d+)/edit-project/$',
        'edit_project', name='edit-project'),

    url(
        r'^(?P<project_id>\d+)/edit-project/add-manufacturer/$',
        'add_manufacturer', name='add_manufacturer'),
    
    url(
        r'^(?P<project_id>\d+)/edit-project/add-location/$',
        'add_location', name='add-location'),

    url(
        r'^(?P<project_id>\d+)/edit-project/add-transmitter/$', 'add_transmitter',
        name='add-transmitter'),

    url(
        r'^(?P<project_id>\d+)/edit-project/add-target/$', 'add_target',
        name='add-target'),

    url(
        r'^(?P<project_id>\d+)/edit-project/add-deployment/$', 'add_deployment',
        name='add-deployment')
)


urlpatterns = patterns('qraatview.views',
  url(r'^ui/', include('qraat_ui.urls', namespace="ui")),
  url(r'^admin/', include(admin.site.urls)),
  url(r'^auth/', include('qraat_auth.urls', namespace="auth")),
  url(r'^jsi18n/$', javascript_catalog),
  url(r'^$', 'index'),
  url(r'^regular-content/$', 'regular_content'),
  url(r'^project/', include((project_patterns, 'qraat', 'qraatview')))
)
