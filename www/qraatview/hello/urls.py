from django.conf.urls.defaults import patterns, include, url
from hello import views
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('hello.views',
    url(r'^list.html', 'list'),
    url(r'^maps4.html', 'maps4'),
)
urlpatterns += patterns('',
  url(r'^admin/', include(admin.site.urls)),
)
