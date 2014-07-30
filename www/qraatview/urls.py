from django.conf.urls import patterns, include, url
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from django.views.i18n import javascript_catalog

admin.autodiscover()

project_patterns = patterns(
    'qraatview.views',

    url(r'^$', 'projects', name='projects'),

    url(r'^create-project/$',
        'create_project', name='create-project'),

    url(
        r'^(?P<project_id>\d+)/$', 'show_project',
        name='show-project'),

    url(
        r'^(?P<project_id>\d+)/manage-locations/$', 'manage_locations',
        name='manage-locations'),

    url(
        r'^(?P<project_id>\d+)/manage-transmitters/$', 'manage_transmitters',
        name='manage-transmitters'),

    url(
        r'^(?P<project_id>\d+)/manage-transmitters/(?P<transmitter_id>\d+)/$',
        'edit_transmitter',
        name='edit-transmitter'),
    
    url(
        r'^(?P<project_id>\d+)/manage-targets/(?P<target_id>\d+)/$',
        'edit_target',
        name='edit-target'),

    url(
        r'^(?P<project_id>\d+)/manage-deployments/$', 'manage_deployments',
        name='manage-deployments'),

    url(
        r'^(?P<project_id>\d+)/manage-targets/$', 'manage_targets',
        name='manage-targets'),

    url(r'^(?P<project_id>\d+)/check-deletion/$', 'check_deletion',
        name='check-deletion'),

    url(r'^(?P<project_id>\d+)/delete-objs/$', 'delete_objs',
        name='delete-objs'),

    url(
        r'^(?P<project_id>\d+)/transmitter/(?P<transmitter_id>\d+)/$',
        'show_transmitter',
        name='show-transmitter'),

    url(
        r'^(?P<project_id>\d+)/location/(?P<location_id>\d+)/$',
        'show_location',
        name='show-location'),
    
    url(
        r'^(?P<project_id>\d+)/target/(?P<target_id>\d+)/$',
        'show_target',
        name='show-target'),

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


urlpatterns = patterns(
    'qraatview.views',
    url(r'^ui/', include('qraat_ui.urls', namespace="ui")),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^auth/', include('qraat_auth.urls', namespace="auth")),
    url(r'^jsi18n/$', javascript_catalog),
    url(r'^$', 'index', name="index"),
    url(r'^project/', include((project_patterns, 'qraat', 'qraatview')))
)
