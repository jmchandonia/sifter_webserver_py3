from django.conf.urls import patterns, include, url
from django.contrib import admin

from django.conf import settings
from django.conf.urls.static import static

from sifter_web.views import get_input,show_results,get_query,get_complexity,navigation_autocomplete


urlpatterns = patterns('',
    # Examples:
    url(r'^$', get_input,name='home'),
    url(r'^results-id=(\d{7})$', show_results,name='results'),
    url(r'^complexity/$', get_complexity,name='complexity'),
    url(r'^query/$', get_query),
    # url(r'^blog/', include('blog.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^autocomplete/', include('autocomplete_light.urls')),
    url(r'^navigationAutocomplete/', navigation_autocomplete, name='navigationAutocomplete'),	
)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)