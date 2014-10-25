from django import forms
from django.shortcuts import render
from django.http import Http404, HttpResponse, HttpResponseRedirect
import datetime
from code.estimate_time import estimate_time, get_processing_time
from chartit import DataPool, Chart
from django.shortcuts import render_to_response
from package.models import Histogram
from django.template import RequestContext, Context, loader

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
                (tableHeader, tableBody) = get_processing_time(pfam)
                if not tableHeader:
                    return render(request, 'query.html', {'form': form, 'response': 'Error'})
            else:
                numTerms = form.cleaned_data['numTerms']
                famSize = form.cleaned_data['famSize']
                (tableHeader, tableBody) = estimate_time(numTerms, famSize)
                # redirect to a new URL:
            return render(request, 'query.html',
                {'form': form, 'response': 'Query submitted', 'tableHeader': tableHeader, 'tableBody': tableBody})
        else:
            return render(request, 'query.html',
                {'form': form, 'response': 'Error'})

    # if a GET (or any other method) we'll create a blank form
    else:
        form = QueryForm()
        return render(request, 'query.html', {'form': form,})

def histogram_view(request):
    # Step 1: Create a DataPool with the data we want to retrieve
    histData = \
        DataPool(
            series=
                [{'options': {
                  'source': Histogram.objects.all()},
                  'terms': [
                    'barHeight',
                    'barWidth']}
                ])
                
    # Step 2: Create the Chart object
    hist = Chart(
            datasource = histData,
            series_options =
              [{'options':{
                    'type': 'column',
                    'stacking': False},
                'terms':[
                    'barHeight',
                    'barWidth']}],
            chart_options =
              {'title': {
                'text': 'Title'},
                'xAxis': {
                    'title': 'x-axis'},
                'yAxis': {
                    'title': 'y-axis'}})
    
    # Step 3: Send the chart object to the template.
    return render_to_response({'hist': hist})
