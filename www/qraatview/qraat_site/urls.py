from django.conf.urls import patterns, include, url
from qraat_site import views

urlpatterns = patterns('qraat_site.views',
	url(r'^$', 'index'),
)
