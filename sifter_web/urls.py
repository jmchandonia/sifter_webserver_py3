from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import re_path
from django.views.static import serve

import os
from sifter_web.views import (
    autocomplete,
    get_complexity,
    get_input,
    show_about,
    show_contact,
    show_domain_predictions,
    show_download,
    show_help,
    show_predictions,
    show_results,
    show_search_options,
)

OUTPUT_DIR=getattr(settings, 'SIFTER_OUTPUT_DIR', os.path.join(os.path.dirname(__file__),"output"))

urlpatterns = [
    re_path(r'^$', get_input, name='home'),
    re_path(r'^help/$', show_help, name='help'),
    re_path(r'^about/$', show_about, name='about'),
    re_path(r'^download/$', show_download, name='download'),
    re_path(r'^contact/$', show_contact, name='contact'),
    re_path(r'^results-id=(\d{7})$', show_results, name='results'),
    re_path(r'^predictions/$', show_predictions, name='predictions'),
    re_path(r'^results-id=(\d{7})/protein=(\w+)$', show_domain_predictions, name='domain_preds'),
    re_path(r'^complexity/$', get_complexity, name='complexity'),
    re_path(r'^search_options/$', show_search_options, name='search_options'),
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^search/$', get_input, name='search'),
    re_path(r'^search/autocomplete$', autocomplete),
    re_path(r'^downloads/(?P<path>.*)$', serve, {'document_root': OUTPUT_DIR}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
