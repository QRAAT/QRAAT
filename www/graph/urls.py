from django.conf.urls import patterns, include, url

urlpatterns = patterns(
    'graph.views',
    url(r'^$', 'graph_home', name='graph_home'),
    url(r'telemetry/$', 'telemetry_graphs', name='telemetry_graphs'),
    url(r'est/$', 'est_graphs', name='est_graphs'),
    url(r'processing/$', 'processing_graphs', name='processing_graphs'),
    url(r'dashboard/$', 'dashboard_page', name='dashboard_page'),
)
