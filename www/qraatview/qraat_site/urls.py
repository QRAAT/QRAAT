from django.conf.urls import patterns, url

urlpatterns = patterns(
    'qraat_site.views',

    url(r'^$', 'index'),

    # url(r'^transmitters/$', 'transmitters'),

    # url(r'^transmitters/(?P<transmitter_id>\d+)/$',
    #     'get_transmitter'),

    url(r'projects/$', 'projects', name='projects'),

    url(r'projects/create-project/$',
        'create_project', name='create-project'),

    url(
        r'^project/(?P<project_id>\d+)/$', 'show_project',
        name='show-project'),

    url(
        r'^project/(?P<project_id>\d+)/transmitter/(?P<transmitter_id>\d+)/$',
        'show_transmitter',
        name='show-transmitter'),

    url(
        r'^project/(?P<project_id>\d+)/location/(?P<location_id>\d+)/$',
        'show_location',
        name='show-location'),

    url(
        r'^project/(?P<project_id>\d+)/edit-project/$',
        'edit_project', name='edit-project'),

    url(
        r'^project/(?P<project_id>\d+)/edit-project/add-manufacturer/$',
        'add_manufacturer', name='add_manufacturer'),

    url(
        r'^project/(?P<project_id>\d+)/edit-project/add-transmitter/$', 'add_transmitter',
        name='add-transmitter'),

    url(
        r'^project/(?P<project_id>\d+)/edit-project/add-target/$', 'add_target',
        name='add-target'),

    url(
        r'^project/(?P<project_id>\d+)/edit-project/add-deployment/$', 'add_deployment',
        name='add-deployment'),

    url(r'^regular-content/$', 'regular_content'),
)
