from django.conf.urls.defaults import patterns, include, url
from hello import views
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('hello.views',
    url(r'^list.html', 'list'),
    url(r'^maps.html', 'add'),
    url(r'^maps2.html', 'maps'),
    url(r'^maps3.html', 'maps3'),
    url(r'^convert.html', 'convert'),
    url(r'^maps4.html', 'maps4'),
    url(r'^prefs.html', 'prefs'),
    url(r'^hello/index.html', 'index'),
    url(r'^hello/(?P<poll_id>\d+)/$', 'detail'),
    url(r'^hello/(?P<poll_id>\d+)/results/$', 'results'),
    url(r'^hello/(?P<poll_id>\d+)/vote/$', 'vote'),
)
urlpatterns += patterns('',
  url(r'^admin/', include(admin.site.urls)),
)
