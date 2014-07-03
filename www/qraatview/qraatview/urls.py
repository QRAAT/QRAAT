from django.conf.urls.defaults import patterns, include, url

from hello import views
from hellotest import views
from qraat_auth import views
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
  url(r'^hello/', include ('hello.urls')),
  url(r'^admin/', include(admin.site.urls)),
  url(r'^hellotest/', include('hellotest.urls')),
  url(r'^auth/', include('qraat_auth.urls', namespace="auth")),
  url(r'^qraat/', include('qraat_site.urls', namespace="qraat")),
)
