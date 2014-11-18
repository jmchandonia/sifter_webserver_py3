import datetime
import itertools
from django import forms
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, render_to_response
from django.template import Context, loader, RequestContext
from chartit import DataPool, Chart
from code.estimate_time import estimate_time, get_processing_time
from estimatedb.models import Errorhistogrambars
from ajax_search.forms import SearchForm


def hello(request):
    return HttpResponse("Hello world")

def current_datetime(request):
    now = datetime.datetime.now()
    return render(request, 'current_datetime.html', {'current_date': now})

def hours_ahead(request, offset):
    try:
        offset = int(offset)
    except ValueError:
        raise Http404()
    dt = datetime.datetime.now() + datetime.timedelta(hours=offset)
    return render(request, 'hours_ahead.html', {'hour_offset': offset, 'next_time': dt})

class QueryForm(forms.Form):
    choices = forms.ChoiceField(widget=forms.RadioSelect, choices=(('pfam', 'Input pfam id',), ('params', 'Input parameters',)))
    pfam = forms.CharField(label='PFAM id', required=False)
    numTerms = forms.IntegerField(label='Number of GO terms', required=False)
    famSize = forms.IntegerField(label='Family size', required=False)


def get_query(request):
    def render_error(response):
        return render(request, 'query.html',
            {'form': form, 'response': response, 'displayHist': False})
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = QueryForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            choices = form.cleaned_data['choices']
            if choices == 'pfam':
                pfam = form.cleaned_data['pfam']
                if not pfam:
                    return render_error('Please enter a PFAM id')
                (tableHeader, tableBody, histograms, chartContainers, numTerms) = get_processing_time(pfam)
                if not tableHeader:
                    return render_error('Error: PFAM id %s is not in the database' % pfam)
            else:
                numTerms = form.cleaned_data['numTerms']
                famSize = form.cleaned_data['famSize']
                if not numTerms or numTerms < 0:
                    return render_error('Please enter a positive integer for the number of GO terms')
                elif not famSize or famSize < 0:
                    return render_error('Please enter a positive integer for the family size')
                (tableHeader, tableBody, histograms, chartContainers, numTerms) = estimate_time(numTerms, famSize)
            if not histograms:
                return render(request, 'query.html', {'form': form,
                    'tableHeader': tableHeader, 'tableBody': tableBody, 'displayHist': False})                
            return render_to_response('query.html',
                {'form': form, 'tableHeader': tableHeader, 'tableBody': tableBody, 'histograms': histograms,
                'displayHist': True, 'chartContainers': chartContainers, 'numTerms': numTerms},
                RequestContext(request))
        else:
            return render(request, 'query.html',
                {'form': form, 'response': 'Error'}, RequestContext(request))

    # if a GET (or any other method) we'll create a blank form
    else:
        form = QueryForm()
        return render(request, 'query.html', {'form': form,})

        
def search_helper(count, query):
    model_list = Taxid.objects.filter(tax_name__icontains=query, status=1)
    for L in range(1, count + 1):
        for subset in itertools.permutations(words, L):
            count1 = 1
            query1 = subset[0]
            while count1 != len(subset):
                query1 = query1 + " " + subset[count1]
                count1 += 1
            model_list = entry_list | Taxid.objects.filter(tax_name__icontains=query, status=1)
    return (model_list.distinct())
