from django.conf.urls import patterns, include, url
from mysite.views import hello, current_datetime, hours_ahead, get_query, histogram_view

urlpatterns = patterns('',
    url(r'^$', hello),
    url(r'^hello/$', hello),
    url(r'^time/$', current_datetime),
    url(r'^time/plus/(\d{1,2})/$', hours_ahead),
    url(r'^query/$', get_query),
    url(r'^hist/$', histogram_view),
)
