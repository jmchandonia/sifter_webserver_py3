from django.conf.urls import patterns, include, url
from django.contrib import admin

from django.conf import settings
from django.conf.urls.static import static

from sifter_web.views import get_input,show_results,get_complexity,do_basic_search,autocomplete

from haystack.views import SearchView, search_view_factory
from haystack.forms import HighlightedSearchForm

urlpatterns = patterns('',
    # Examples:
    url(r'^$', get_input,name='home'),
    url(r'^results-id=(\d{7})$', show_results,name='results'),
    url(r'^complexity/$', get_complexity,name='complexity'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^autocomplete/', include('autocomplete_light.urls')),
	url(r'^search/', include('haystack.urls')),
	url(r'^search/autocomplete', autocomplete),
	url(r'^search3/', do_basic_search),
)
urlpatterns += patterns('haystack.views',
    url(r'^search4/', search_view_factory(
        view_class=	SearchView,
        template='search/autocomplete.html',
        form_class=HighlightedSearchForm,
    ), name='haystack_search2'),
)
urlpatterns += patterns('haystack.views',
    url(r'^search2/', search_view_factory(
        view_class=	SearchView,
        template='search/search2.html',
        form_class=HighlightedSearchForm,
    ), name='haystack_search2'),
)


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)