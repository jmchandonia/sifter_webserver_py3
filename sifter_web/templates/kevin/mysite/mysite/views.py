from django import forms
from django.shortcuts import render
from django.http import Http404, HttpResponse, HttpResponseRedirect
import datetime
from code.estimate_time import estimate_time, get_processing_time
from chartit import DataPool, Chart
from django.shortcuts import render_to_response
from graphs.models import Histogram, ErrorHistogramBarsTmp
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
                (tableHeader, tableBody, histogram) = get_processing_time(pfam)
                if not tableHeader:
                    return render(request, 'query.html', {'form': form, 'response': 'Error'}, RequestContext(request))
            else:
                numTerms = form.cleaned_data['numTerms']
                famSize = form.cleaned_data['famSize']
                (tableHeader, tableBody, histogram) = estimate_time(numTerms, famSize)
                # redirect to a new URL:
            return render_to_response('query.html',
                {'form': form, 'response': 'Query submitted', 'tableHeader': tableHeader, 'tableBody': tableBody, 'histogram': histogram, 'displayHist': True}, RequestContext(request))
        else:
            return render(request, 'query.html',
                {'form': form, 'response': 'Error'}, RequestContext(request))

    # if a GET (or any other method) we'll create a blank form
    else:
        form = QueryForm()
        return render(request, 'query.html', {'form': form,})

def histogram_view(request):
    # points = [(2, 6), (3, 5), (4, 7), (1, 8), (5, 4)]
    # for point in points:
        # h = Histogram.objects.create(barWidth=point[0], barHeight=point[1])
        # h.save()
    # ns = [0.0, 1081.0, 515.0, 0.0, 0.0, 0.0, 0.0, 0.0, 858.0, 0.0, 0.0, 136.0, 751.0, 661.0, 756.0, 889.0, 978.0, 830.0, 535.0, 0.0, 295.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 455.0, 0.0, 0.0, 508.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 192.0]
    # bins = [0.0, 0.22787811916610751, 0.45575623833221501, 0.68363435749832258, 0.91151247666443003, 1.1393905958305375, 1.3672687149966452, 1.5951468341627526, 1.8230249533288601, 2.0509030724949677, 2.278781191661075, 2.5066593108271826, 2.7345374299932903, 2.9624155491593975, 3.1902936683255052, 3.4181717874916124, 3.6460499066577201, 3.8739280258238278, 4.1018061449899355, 4.3296842641560422, 4.5575623833221499, 4.7854405024882576, 5.0133186216543653, 5.2411967408204729, 5.4690748599865806, 5.6969529791526874, 5.9248310983187951, 6.1527092174849027, 6.3805873366510104, 6.6084654558171181, 6.8363435749832249, 7.0642216941493325, 7.2920998133154402, 7.5199779324815479, 7.7478560516476556, 7.9757341708137623, 8.2036122899798709, 8.4314904091459777, 8.6593685283120845, 8.887246647478193, 9.1151247666442998, 9.3430028858104084, 9.5708810049765152, 9.798759124142622, 10.026637243308731, 10.254515362474837, 10.482393481640946, 10.710271600807053, 10.938149719973161, 11.166027839139268]
    # for i in range(len(ns)):
        # h = Histogram.objects.create(barWidth=bins[i], barHeight=ns[i])
        # h.save()
    data = []
    for h in Histogram.objects.all():
        data.append((h.barHeight, h.barWidth))
    print 'length'
    print len(ErrorHistogramBars.objects.all())

    cat = (3, 2)
    # Step 1: Create a DataPool with the data we want to retrieve
    histData = \
        DataPool(
            series=
                [{'options': {
                  'source': ErrorHistogramBars.objects.filter(numelCat=cat[0]).filter(famSizeCat=cat[1])},
                  'terms': [
                    'bin',
                    'barHeight']}
                ])
    
    # Step 2: Create the Chart object
    hist = Chart(
            datasource = histData,
            series_options =
              [{'options':{
                    'type': 'column',
                    'pointPadding': 0,
                    'borderWidth': 0,
                    'groupPadding': 0,
                    'shadow': False,
                    'stacking': False},
                'terms':{
                    'bin': [
                        'barHeight',]
                    }}],
            chart_options =
              {'title': {
                'text': 'Distribution of estimated time'},
                'tooltip': {
                    'formatter': 'function() { return false; }',
                },
                'xAxis': {
                    'labels': {
                        'enabled': True,
                    },
                    'title': {
                        'text': 'Estimated time'},
                    'tickColor': '#000000',
                    'tickInterval': 5,
                    'tickmarkPlacement': 'between',
                    'type': 'linear',
                    },
                'yAxis': {
                    'labels': {
                        'enabled': False,
                    },
                    'title': {
                        'text': 'Probability'}}},

                )

    #for h in Histogram.objects.all():
    #    print h.barHeight, h.barWidth
    print histData
    
    # Step 3: Send the chart object to the template.
    return render_to_response('chart.html', {'hist': hist, 'data': data})
