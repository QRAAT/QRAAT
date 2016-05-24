from django.conf.urls import patterns, include, url
from account import views

urlpatterns = patterns('account.views',
    url(r'^$', 'index'),
    url(r'^login/$', 'user_login', name='login'),
    url(r'^users/$', 'show_users', name="users"),
    url(r'^users/user-account/(?P<user_id>\d+)/$', 'user_account', name="user-account-id"),
    url(r'user-account/$', 'user_account', name="user-account"),
    url(r'^change-password/$', 'change_password', name='change-password'),
    url(r'^edit-user/$', 'edit_account', name='edit-account'),
    url(r'^logout/$', 'user_logout', name="logout"),
)
