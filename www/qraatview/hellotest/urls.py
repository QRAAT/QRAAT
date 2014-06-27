from django.conf.urls import patterns, include, url
from hello import views
from hellotest import views
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('hellotest.views',
    url(r'^index.html', 'index'),
)

urlpatterns += patterns('',
  url(r'^admin/', include(admin.site.urls)),
)
