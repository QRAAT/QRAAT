from django.conf.urls import patterns, include, url
from qraat_ui import views
from qraat_auth import views
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
  url(r'^qraat_ui/', include('qraat_ui.urls', namespace="ui")),
  url(r'^admin/', include(admin.site.urls)),
  url(r'^auth/', include('qraat_auth.urls', namespace="auth")),
  url(r'^qraat/', include('qraat_site.urls', namespace="qraat")),
)
