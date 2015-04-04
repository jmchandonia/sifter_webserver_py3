from django.conf.urls import patterns, include, url
from django.contrib import admin

from django.conf import settings
from django.conf.urls.static import static

from sifter_web.views import get_input,show_results,get_complexity,autocomplete,show_predictions,show_help,show_about,show_search_options,show_download,show_contact,show_domain_predictions

from haystack.views import SearchView, search_view_factory
from haystack.forms import HighlightedSearchForm
import os

OUTPUT_DIR=os.path.join(os.path.dirname(__file__),"output")

urlpatterns = patterns('',
    # Examples:
    url(r'^$', get_input,name='home'),
    url(r'^help/', show_help,name='help'),
    url(r'^about/', show_about,name='about'),
    url(r'^download/', show_download,name='download'),
    url(r'^contact/', show_contact,name='contact'),	
    url(r'^results-id=(\d{7})$', show_results,name='results'),
    url(r'^predictions/$', show_predictions,name='predictions'),
    url(r'^domain_preds/$', show_domain_predictions,name='domain_preds'),
    url(r'^complexity/$', get_complexity,name='complexity'),
    url(r'^search_options/$', show_search_options,name='search_options'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^search/', include('haystack.urls')),
    url(r'^search/autocomplete', autocomplete),
    url(r'^downloads/(?P<path>.*)$', 'django.views.static.serve', {'document_root': OUTPUT_DIR}),
)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)