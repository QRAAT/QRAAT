from django.conf.urls import patterns, url

urlpatterns = patterns(
    'qraat_site.views',

    url(r'^$', 'index'),

    url(r'^transmitters/$', 'transmitters'),

    url(r'^transmitters/(?P<transmitter_id>\d+)/$',
        'get_transmitter'),

    url(
        r'^project/(?P<project_id>\d+)/$', 'show_project',
        name='show-project'),

    url(r'^regular-content/$', 'regular_content'),
)
