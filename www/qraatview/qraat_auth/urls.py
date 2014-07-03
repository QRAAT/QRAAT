from django.conf.urls import patterns, include, url
from qraat_auth import views

urlpatterns = patterns('qraat_auth.views',
	url(r'^$', 'index'),
	url(r'^login/$', 'user_login', name='login'),
	url(r'^login/logged-in/$', 'user_logged_in'),
	url(r'^create-user/$', 'createUserForm', name='create-user'),
	url(r'^create-user/user-created/$', 'userCreated'),
	url(r'^logout/$', 'user_logout'),
)
