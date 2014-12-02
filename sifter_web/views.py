from django.shortcuts import render,render_to_response,RequestContext
#from django.template import  Context
#from django.template.loader import get_template
from django import forms
from django.http import HttpResponseRedirect,HttpResponse,Http404
from django.core.exceptions import ValidationError
from django.forms.util import ErrorList
from sifter_web.tasks import run_sifter_job
from results.models import SIFTER_Output
import datetime
import random
import pickle
import os
import time
from chartit import DataPool, Chart
from scripts.estimate_time import estimate_time, get_processing_time
from estimatedb.models import Errorhistogrambars
import numpy as np
from django.db.models import Q as Q_lookup
import autocomplete_light
from haystack.query import SearchQuerySet
from haystack.forms import SearchForm
from haystack.query import EmptySearchQuerySet
from django.core.paginator import Paginator, InvalidPage
from django.conf import settings
RESULTS_PER_PAGE = getattr(settings, 'HAYSTACK_SEARCH_RESULTS_PER_PAGE', 20)
import json

INPUT_DIR=os.path.join(os.path.dirname(__file__),"input")
OUTPUT_DIR=os.path.join(os.path.dirname(os.path.dirname(__file__)),"output")

class InputForm(forms.Form):
    #input_any = autocomplete_light.ChoiceField('TermAutocomplete')
    input_any = forms.CharField(widget=forms.Textarea(attrs={'rows':1, 'placeholder':'Enter your queries','class':'form-control','id':'input_any'}),label='Input Any Queries', max_length=100000,required=False)
    input_queries = forms.CharField(widget=forms.Textarea(attrs={'rows':3, 'placeholder':'Enter query proteins','class':'form-control','id':'input_queries'}),label='Input Queries', max_length=100000,required=False)
    query_uploader = forms.FileField(widget=forms.FileInput(attrs={'id':'query_uploader'}),required=False)
    input_species = forms.CharField(widget=forms.TextInput(attrs={'placeholder':'Enter query species Taxonomy ID','class':'form-control','id':'input_species'}),label='Input Species', max_length=1000,required=False)
    input_function = forms.CharField(widget=forms.Textarea(attrs={'rows':3, 'placeholder':'Enter query functions','class':'form-control','id':'input_function'}),label='Input Function', max_length=100000,required=False)
    function_uploader = forms.FileField(widget=forms.FileInput(attrs={'id':'function_uploader'}),required=False)
    input_function_sp = forms.CharField(widget=forms.Textarea(attrs={'rows':1, 'placeholder':'Enter query functions','class':'form-control','id':'input_function_sp'}),label='Input Function Sp', max_length=100000,required=False)
    input_sequence = forms.CharField(widget=forms.Textarea(attrs={'rows':10, 'placeholder':'Enter query sequences','class':'form-control','id':'input_sequence'}),label='Input Sequences', max_length=100000,required=False)
    sequence_uploader = forms.FileField(widget=forms.FileInput(attrs={'id':'sequence_uploader'}),required=False)
    input_email = forms.CharField(widget=forms.EmailInput(attrs={'id':'input_email','placeholder':'Enter email','class':'form-control',}),label='Input Email', max_length=100,required=False)
    sifter_choices = forms.ChoiceField(widget=forms.RadioSelect, choices=(('EXP-Model', 'Only use experimental evidence (SIFTER EXP-Model)',)
        , ('ALL-Model', 'Use both experimental and non-experimental evidence (SIFTER ALL-Model)',)),initial='EXP-Model',required=False)
    active_tab_hidden = forms.CharField(widget=forms.HiddenInput(attrs={'id':'active_tab_hidden'}),initial='by_any',required=False)
    ExpWeight_hidden = forms.CharField(widget=forms.HiddenInput(attrs={'id':'ExpWeight_hidden'}),initial='0.7',required=False)
    more_options_hidden= forms.BooleanField(widget=forms.HiddenInput(attrs={'id':'more_options_hidden'}),initial=False,required=False)

    
    def check(self,cleaned_data,my_fields,msg):
        enered_field=[]
        for my_field in my_fields:            
            my_field_data = cleaned_data.get(my_field)
            if not my_field_data:
                enered_field.append(my_field)
        if not (set(my_fields)-set(enered_field)):
            for my_field in my_fields:
                my_field_data = cleaned_data.get(my_field)
                if not my_field_data:                    
                    self._errors[my_field] = ErrorList([msg])
                    break
    
    def clean(self):
        active_tab=self.cleaned_data['active_tab_hidden']
        cleaned_data = super(InputForm, self).clean()
        if active_tab=='by_protein':
            self.check(cleaned_data,['input_queries','query_uploader'],'Query proteins are not entered.')
        elif active_tab=='by_species':
            self.check(cleaned_data,['input_species'],'Species IDs are not entered.')
        elif active_tab=='by_function':
            self.check(cleaned_data,['input_function','function_sp_uploader'],'GO term IDs are not entered.')
            self.check(cleaned_data,['input_function_sp','function_sp_uploader'],'Species IDs are not entered.')            
        elif active_tab=='by_sequence':
            self.check(cleaned_data,['input_sequence','sequence_uploader'],'Query sequences are not entered.')


        #if self.cleaned_data['input_queries']!='1':
        #    msg = 'The type and organisssszation do not match.'
        #    self._errors['input_queries'] = ErrorList([msg])
        #    del self.cleaned_data['input_queries']
                
        return self.cleaned_data

    def set_default(self,field,value):
        data = self.data.copy()
        data[field] = value
        self.data = data
        
class MySearchForm(SearchForm):
    #q = forms.CharField(required=False, widget=forms.TextInput(attrs={'type': 'text'}))
    q=forms.CharField(widget=forms.TextInput(attrs={'rows':1, 'placeholder':'Enter your queries','class':'form-control'}),label='Input Any Queries', max_length=100000,required=False)

    def no_query_found(self):
        return self.searchqueryset.all()

    def search(self):
        # First, store the SearchQuerySet received from other processing.
        sqs = SearchQuerySet()

        if not self.is_valid():
            return self.no_query_found()

        # Check to see if a q was chosen.
        if self.cleaned_data['q']:		
            sqs1 = sqs.filter(content_auto_name=self.cleaned_data['q'])
            sqs2 = sqs.filter(content_auto_acc=self.cleaned_data['q'])            
            sqs3 = sqs.filter(content_auto_taxname=self.cleaned_data['q'])
            sqs4 = sqs.filter(content_auto_taxid=self.cleaned_data['q'])
            sqs5 = sqs.filter(text=self.cleaned_data['q'])
            sqs=sqs5|sqs1|sqs2|sqs3|sqs4
            sqs_term=sqs.filter(django_ct='term_db.term')            
            sqs_taxid=sqs.filter(django_ct='taxid_db.taxid')
        return [{'model':'Species','results':sqs_taxid},{'model':'Functions','results':sqs_term}]

class EstimateForm(forms.Form):
    estim_choices = forms.ChoiceField(widget=forms.RadioSelect, choices=(('params', 'Customized Input',),('pfam', 'Use a Pfam ID',)),initial='params')
    pfam = forms.CharField(label='PFAM ID', required=False)
    numTerms = forms.IntegerField(label='Number of candidate functions', required=False)
    famSize = forms.IntegerField(label='Family size', required=False)

'''def get_query(request):
    def render_error(response):
        return render(request, 'query.html',
            {'form': form, 'response': response, 'displayHist': False})
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = EstimateForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            choices = form.cleaned_data['estim_choices']
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
        form = EstimateForm()
        return render(request, 'query.html', {'form': form,})

'''
def get_complexity(request):
    def render_error(response):
        return render(request, 'complexity.html',
            {'form': form, 'response': response, 'displayHist': False})
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = EstimateForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            choices = form.cleaned_data['estim_choices']
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
                return render(request, 'complexity.html', {'form': form,
                    'tableHeader': tableHeader, 'tableBody': tableBody, 'displayHist': False})                
            print chartContainers
            return render_to_response('complexity.html',
                {'form': form, 'tableHeader': tableHeader, 'tableBody': tableBody, 'histograms': histograms,
                'displayHist': True, 'chartContainers': chartContainers, 'numTerms': numTerms},
                RequestContext(request))
        else:
            return render(request, 'complexity.html',
                {'form': form, 'response': 'Error'}, RequestContext(request))

    # if a GET (or any other method) we'll create a blank form
    else:
        form = EstimateForm()
        return render(request, 'complexity.html', {'form': form,})

def delete_old_results():
    olddate = datetime.date.today()+datetime.timedelta(days=-15)
    old_job_ids=SIFTER_Output.objects.filter(result_date__lte=olddate).values_list('job_id',flat=True)
    for job_id in old_job_ids:
        print job_id
        infile=os.path.join(INPUT_DIR,"%s_input.pickle"%job_id)
        if os.path.exists(infile):
            os.remove(infile)
        outfile=os.path.join(OUTPUT_DIR,"%s_output.pickle"%job_id)
        if os.path.exists(outfile):
            os.remove(outfile)
    
    

def get_input(request):
    
    searchqueryset=None
    load_all=True
    context_class=RequestContext
    extra_context=None
    results_per_page=None
    query = ''
    results = EmptySearchQuerySet()
    search_form = MySearchForm(searchqueryset=searchqueryset, load_all=load_all)
    pages = ''
    paginators=''
    context = {
        'search_form': search_form,
        'pages': pages,
        'paginators': paginators,
        'query': query,
        'suggestion': None,
    }
    if results.query.backend.include_spelling:
        context['suggestion'] = search_form.get_suggestion()
    spelling = results.spelling_suggestion(query)
    context['suggestion']= spelling

    if extra_context:
        context.update(extra_context)
            
        
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = InputForm(request.POST,request.FILES)
        # check whether it's valid:

        if form.is_valid():
            active_tab=form.cleaned_data['active_tab_hidden']
            form.set_default('active_tab_hidden',active_tab)
            more_options=form.cleaned_data['more_options_hidden']
            form.set_default('more_options_hidden',more_options)
            sifter_choices_val=form.cleaned_data['sifter_choices']
            form.set_default('sifter_choices',sifter_choices_val)
            
            if active_tab=='by_any':                
                return render_to_response('home.html', context, context_instance=context_class(request))        
            else:
                job_id=random.randint(1000000,9999999)
                while SIFTER_Output.objects.filter(job_id=job_id):
                    job_id=random.randint(1000000,9999999)
                print job_id
                
                infile=os.path.join(INPUT_DIR,"%s_input.pickle"%job_id)
                my_species=''
                my_functions=[]
                my_proteins=[]
                n_sequences=0
                if active_tab=='by_protein':
                    my_proteins=[w for w in form.cleaned_data['input_queries'].split(',')]
                    data={'proteins':my_proteins}
                elif active_tab=='by_species':
                    my_species=form.cleaned_data['input_species']
                    data={'species':my_species}
                elif active_tab=='by_function':
                   my_species=form.cleaned_data['input_function_sp']
                   my_functions=[w for w in form.cleaned_data['input_function'].split(',')]
                   data={'species':form.cleaned_data['input_function_sp'],'functions':my_functions}                
                elif active_tab=='by_sequence':
                    my_sequences=form.cleaned_data['input_sequence']
                    n_sequences=len(my_sequences)
                    data={'sequences':my_sequences}                
                pickle.dump(data,open(infile,'w'))
                P=SIFTER_Output(job_id=job_id,exp_weight=form.cleaned_data['ExpWeight_hidden'], email = form.cleaned_data['input_email'],
                                query_method=active_tab, sifter_EXP_choices = True if sifter_choices_val=='EXP-Model' else False,
                                n_proteins=len(my_proteins),n_species=len(my_species),n_functions=len(my_functions),n_sequences=n_sequences,submission_date=datetime.date.today(),
                                result_date=datetime.date.today(),input_file=infile,output_file='')
                P.save()
                delete_old_results()
                my_form_data={'sifter_choices':form.cleaned_data['sifter_choices'],'ExpWeight_hidden':form.cleaned_data['ExpWeight_hidden']
                              ,'active_tab_hidden':form.cleaned_data['active_tab_hidden']}
                run_sifter_job.delay(my_form_data,job_id)
                return HttpResponseRedirect('/results-id=%s'%job_id, {'results':''})
        else:
            active_tab=form.cleaned_data['active_tab_hidden']
            form.set_default('active_tab_hidden',active_tab)
            more_options=form.cleaned_data['more_options_hidden']
            form.set_default('more_options_hidden',more_options)
            sifter_choices_val=form.cleaned_data['sifter_choices']
            form.set_default('sifter_choices',sifter_choices_val)
            
            context['form']=form
            context['response']=form.cleaned_data['ExpWeight_hidden']        

            return render_to_response('home.html', context, context_instance=context_class(request))        

    # if a GET (or any other method) we'll create a blank form
    else:
        if request.GET.get('q'):    
            #search form processing
            search_form = MySearchForm(request.GET, searchqueryset=searchqueryset, load_all=load_all)
            if search_form.is_valid():
                query = search_form.cleaned_data['q']
                print query
                results = search_form.search()
        else:
            search_form = MySearchForm(searchqueryset=searchqueryset, load_all=load_all)
        
        paginators=[]
        pages=[]
        for i,result in enumerate(results):
            paginator=Paginator(result['results'], results_per_page or RESULTS_PER_PAGE)
            paginators.append(paginator)
            try:
                pages.append({'model':result['model'],'page':paginator.page(int(request.GET.get('page-%s'%i, 1)))})
            except InvalidPage:
                raise Http404("No such page of results!")
                
        context = {
            'search_form': search_form,
            'pages': pages,
            'paginators': paginators,
            'query': query,
            'suggestion': None,
        }
        for result in results:
            if result['results'].query.backend.include_spelling:
                context['suggestion'] = search_form.get_suggestion()
            spelling = result['results'].spelling_suggestion(query)
            context['suggestion']= spelling
        
        if extra_context:
            context.update(extra_context)
        
        #other form processing    
        form = InputForm()
        context['form']=form
        context['response']='Hi'        
        return render_to_response('home.html', context, context_instance=context_class(request))        
        

    #return render(request, 'home.html', context)



def show_results(request,job_id):
    results_per_page=20
    time.sleep(0.5)
    my_object=SIFTER_Output.objects.filter(job_id=job_id)
    my_msg=[]
    if not len(my_object)==1:
        my_msg.append(['danger','Error in the job_id. Number of hits=%s'%(len(my_object))])       
        return render(request, 'results.html', {'my_object':'','result':'','pending':False,'my_msg':my_msg})
    my_object=my_object[0]
    print my_object.input_file,my_object.output_file
    if my_object.output_file=='':
        my_msg.append(['warning','Thanks! You have successfully submitted your SIFTER query.'])
        return render(request, 'results.html', {'my_object':my_object,'result':'','pending':False,'my_msg':my_msg})        
    else:
        my_msg.append(['info','Your SIFTER query results are ready.'])
        results=pickle.load(open(my_object.output_file))
        paginator = Paginator(results['result'], results_per_page)
        try:
            page = paginator.page(int(request.GET.get('page', 1)))
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            page = paginator.page(1)
        except EmptyPage:
            page = paginator.page(paginator.num_pages)
            
        return render(request, 'results.html', {'my_object':my_object,'result':page,'pending':False,'my_msg':my_msg})
        
            
def autocomplete(request):
    sqs=SearchQuerySet()
    sqs1 = sqs.autocomplete(content_auto_name=request.GET.get('q', ''))[:5]
    sqs2 = sqs.autocomplete(content_auto_acc=request.GET.get('q', ''))[:5]    
    sqs3 = sqs.autocomplete(content_auto_taxname=request.GET.get('q', ''))[:5]
    sqs4 = sqs.autocomplete(content_auto_taxid=request.GET.get('q', ''))[:5]
    sqs5 = sqs.filter(text=request.GET.get('q', ''),django_ct='term_db.term')[:5]
    sqs6 = sqs.filter(text=request.GET.get('q', ''),django_ct='taxid_db.taxid')[:5]
    suggestions1 = ["%s (%s)"%(result.object.name,result.object.acc) for result in sqs5+sqs1+sqs2]    
    suggestions2 = ["%s (taxid:%s)"%(result.object.tax_name,result.object.tax_id) for result in sqs6+sqs3+sqs4]    
    suggestions=suggestions1+suggestions2
    # Make sure you return a JSON object, not a bare list.
    # Otherwise, you could be vulnerable to an XSS attack.
    the_data = json.dumps({
        'results': suggestions
    })
    return HttpResponse(the_data, content_type='application/json')

    
def do_basic_search(request, template='search/search.html', load_all=True, form_class=MySearchForm, searchqueryset=None, context_class=RequestContext, extra_context=None, results_per_page=None):
    query = ''
    results = EmptySearchQuerySet()
    if request.GET.get('q'):
        form = form_class(request.GET, searchqueryset=searchqueryset, load_all=load_all)

        if form.is_valid():
            query = form.cleaned_data['q']
            results = form.search()
            results=results[0]['results']|results[1]['results']
    else:
        form = form_class(searchqueryset=searchqueryset, load_all=load_all)

    paginator = Paginator(results, results_per_page or RESULTS_PER_PAGE)
    try:
        page = paginator.page(int(request.GET.get('page', 1)))
    except InvalidPage:
        raise Http404("No such page of results!")

    context = {
        'form': form,
        'page': page,
        'paginator': paginator,
        'query': query,
        'suggestion': None,
    }

    if results.query.backend.include_spelling:
        context['suggestion'] = form.get_suggestion()

    spelling = results.spelling_suggestion(query)
    context['suggestion']= spelling
    print 'spelling',spelling,results.query.backend.include_spelling,SearchQuerySet().spelling_suggestion('protain')

    if extra_context:
        context.update(extra_context)

    return render_to_response(template, context, context_instance=context_class(request))