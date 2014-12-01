from django.shortcuts import render,render_to_response,RequestContext
#from django.template import  Context
#from django.template.loader import get_template
from django import forms
from django.http import HttpResponseRedirect,HttpResponse
from django.core.exceptions import ValidationError
from django.forms.util import ErrorList
from sifter_web.tasks import run_sifter_job
from results.models import SIFTER_Output
from taxid_db.models import Taxid
import datetime
import random
import pickle
from term_db.models import Term
import os
import operator
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
    my_search_field = forms.CharField(required=False)

    def no_query_found(self):
        return self.searchqueryset.all()

    def search(self):
        # First, store the SearchQuerySet received from other processing.
        sqs = super(MySearchForm, self).search()

        if not self.is_valid():
            return self.no_query_found()

        # Check to see if a my_search_field was chosen.
        if self.cleaned_data['my_search_field']:
            sqs1 = sqs.filter(content_auto_name=self.cleaned_data['my_search_field'])
            sqs2 = sqs.filter(content_auto_acc=self.cleaned_data['my_search_field'])            
            sqs3 = sqs.filter(content_auto_taxname=self.cleaned_data['my_search_field'])
            sqs4 = sqs.filter(content_auto_taxid=self.cleaned_data['my_search_field'])
            sqs5=sqs.filter(text=self.cleaned_data['my_search_field'])
            sqs=sqs5|sqs1|sqs2|sqs3|sqs4

        return sqs

class EstimateForm(forms.Form):
    estim_choices = forms.ChoiceField(widget=forms.RadioSelect, choices=(('params', 'Customized Input',),('pfam', 'Use a Pfam ID',)),initial='params')
    pfam = forms.CharField(label='PFAM ID', required=False)
    numTerms = forms.IntegerField(label='Number of candidate functions', required=False)
    famSize = forms.IntegerField(label='Family size', required=False)

def get_query(request):
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


def get_input(request):
    
    searchqueryset=None
    load_all=True
    context_class=RequestContext
    extra_context=None
    results_per_page=None
    query = ''
    results = EmptySearchQuerySet()

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = InputForm(request.POST,request.FILES)
        search_form = MySearchForm(request.POST, searchqueryset=searchqueryset, load_all=load_all)
        # check whether it's valid:

        if form.is_valid() and search_form.is_valid():
            active_tab=form.cleaned_data['active_tab_hidden']
            form.set_default('active_tab_hidden',active_tab)
            more_options=form.cleaned_data['more_options_hidden']
            form.set_default('more_options_hidden',more_options)
            sifter_choices_val=form.cleaned_data['sifter_choices']
            form.set_default('sifter_choices',sifter_choices_val)
            
            if active_tab=='by_any':                
                query = search_form.cleaned_data['my_search_field']
                print query
                results = search_form.search()
                paginator = Paginator(results, results_per_page or RESULTS_PER_PAGE)

                try:
                    page = paginator.page(int(request.GET.get('page', 1)))
                except InvalidPage:
                    raise Http404("No such page of results!")

                context = {
                    'search_form': search_form,
                    'page': page,
                    'paginator': paginator,
                    'query': query,
                    'suggestion': None,
                }

                if results.query.backend.include_spelling:
                    context['suggestion'] = search_form.get_suggestion()

                spelling = results.spelling_suggestion(query)
                context['suggestion']= spelling

                if extra_context:
                    context.update(extra_context)
                
                context['form']=form
                context['response']='Hi'        
                return render_to_response('home.html', context, context_instance=context_class(request))        
            else:
                job_id=random.randint(1000000,9999999)
                while SIFTER_Output.objects.filter(job_id=job_id):
                    job_id=random.randint(1000000,9999999)
                print job_id
                
                infile=os.path.join(INPUT_DIR,"%s_input.pickle"%job_id)
                if active_tab=='by_protein':
                    data={'proteins':[w for w in form.cleaned_data['input_queries'].split(',')]}
                elif active_tab=='by_species':
                    data={'species':form.cleaned_data['input_species']}                
                elif active_tab=='by_function':
                    data={'species':form.cleaned_data['input_function_sp'],'functions':[w for w in form.cleaned_data['input_function'].split(',')]}                
                elif active_tab=='by_sequence':
                    data={'sequences':form.cleaned_data['input_sequence']}                
                pickle.dump(data,open(infile,'w'))
                P=SIFTER_Output(job_id=job_id,exp_weight=form.cleaned_data['ExpWeight_hidden'], email = form.cleaned_data['input_email'],
                                query_method=active_tab, sifter_EXP_choices = True if sifter_choices_val=='EXP-Model' else False,
                                n_proteins=0,n_species=0,n_functions=0,n_sequences=0,submission_date=datetime.date.today(),
                                result_date=datetime.date.today(),input_file=infile,output_file='')
                P.save()
                
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

            return render(request, 'home.html', {'form': form, 'response':form.cleaned_data['ExpWeight_hidden']})            

    # if a GET (or any other method) we'll create a blank form
    else:
        #search form processing
        search_form = MySearchForm(searchqueryset=searchqueryset, load_all=load_all)
        paginator = Paginator(results, results_per_page or RESULTS_PER_PAGE)

        try:
            page = paginator.page(int(request.GET.get('page', 1)))
        except InvalidPage:
            raise Http404("No such page of results!")

        context = {
            'search_form': search_form,
            'page': page,
            'paginator': paginator,
            'query': query,
            'suggestion': None,
        }
        if results.query.backend.include_spelling:
            context['suggestion'] = search_form.get_suggestion()
        spelling = results.spelling_suggestion(query)
        context['suggestion']= spelling

        if extra_context:
            context.update(extra_context)
        
        #other form processing    
        form = InputForm()
        context['form']=form
        context['response']='Hi'        
        return render_to_response('home.html', context, context_instance=context_class(request))        
        

    #return render(request, 'home.html', context)



def find_go_name_acc(ts):
    res0=[]
    batchs=100
    for i in range(0,int(np.ceil(float(len(ts))/float(batchs)))):
        print i
        res0.extend(Term.objects.filter(term_id__in=ts[batchs*i:min(len(ts),batchs*(i+1))]).values('term_id','name','acc'))
    print len(res0)
    idx_to_go_name={}
    for w in res0:
        idx_to_go_name[w['term_id']]=[w['acc'],w['name']]
    return idx_to_go_name

def show_results(request,job_id):
    time.sleep(0.5)
    my_object=SIFTER_Output.objects.filter(job_id=job_id)
    my_msg=[]
    if not len(my_object)==1:
        my_msg.append(['danger','Error in the job_id. Number of hits=%s'%(len(my_object))])       
        return render(request, 'results.html', {'my_object':'','result':'','pending':False,'my_msg':my_msg})
    my_object=my_object[0]
    print my_object.input_file,my_object.output_file
    if my_object.output_file=='':
        my_msg.append(['info','Thanks! You have successfully submitted your SIFTER query.'])
        return render(request, 'results.html', {'my_object':my_object,'result':'','pending':False,'my_msg':my_msg})        
    else:
        my_msg.append(['info','Your SIFTER query results are ready.'])
        if not my_object.query_method=='by_sequence':
            res,taxids,unip_accs=pickle.load(open(my_object.output_file))
            terms=list(set([v for w in res.values() for v in w]))
            print len(terms)
            print len(res)
            idx_to_go_name=find_go_name_acc(terms)
            result=[]
            for j,gene in enumerate(res):
                print gene
                preds=[]            
                res_sorted=sorted(res[gene].iteritems(),key=operator.itemgetter(1),reverse=True)
                tax_obj=Taxid.objects.filter(tax_id=taxids[gene])
                if tax_obj:
                    tax_name=tax_obj[0].tax_name
                else:
                    tax_name=taxids[gene]
                if len(res_sorted)<=2:
                    end_i=len(res)
                else:
                    end_i=[i for  i, pred  in enumerate(res_sorted) if pred[1]>(res_sorted[1][1]*.75)]
                    if end_i:
                       end_i=end_i[-1]
                    else:
                       end_i=1
    
                for i, pred  in enumerate(res_sorted):
                    term,score=pred
                    if i<=end_i:                    
                        preds.append([idx_to_go_name[term][0],idx_to_go_name[term][1],str(score)])
                    else:
                        break
                result.append([gene,unip_accs[gene],tax_name,taxids[gene],preds])

            print my_object.query_method
            if my_object.query_method == 'by_protein':
                data=pickle.load(open(my_object.input_file))
                my_genes=data['proteins']
                rest=set(my_genes)-set(res.keys())
                print len(set(my_genes))
                for j,gene in enumerate(rest):
                    result.append([gene,'?','?','?',[]])        
        
    
            return render(request, 'results.html', {'my_object':my_object,'result':result,'pending':False,'my_msg':my_msg})
            
        else:
            res,taxids,unip_accs,blast_hits,connected=pickle.load(open(my_object.output_file))
            print res
            terms=list(set([v for w in res.values() for v in w]))
            idx_to_go_name=find_go_name_acc(terms)
            result=[]
            print res.keys()
            for query, hits in blast_hits.iteritems():
                result_q=[]
                for j,hit in enumerate(hits):
                    preds=[]
                    gene=hit[0]
                    if gene not in res:
                        print gene
                        continue
                    res_sorted=sorted(res[gene].iteritems(),key=operator.itemgetter(1),reverse=True)
                    tax_obj=Taxid.objects.filter(tax_id=taxids[gene])
                    if tax_obj:
                        tax_name=tax_obj[0].tax_name
                    else:
                        tax_name=taxids[gene]
                    if len(res_sorted)<=2:
                        end_i=len(res)
                    else:
                        end_i=[i for  i, pred  in enumerate(res_sorted) if pred[1]>(res_sorted[1][1]*.75)]
                        if end_i:
                           end_i=end_i[-1]
                        else:
                           end_i=1
        
                    for i, pred  in enumerate(res_sorted):
                        term,score=pred
                        if i<=end_i:                    
                            preds.append([idx_to_go_name[term][0],idx_to_go_name[term][1],str(score)])
                        else:
                            break
                    result_q.append([gene,unip_accs[gene],tax_name,taxids[gene],hit[1],hit[2],'%0.0f'%hit[3],preds])
                result.append([query,result_q])
            return render(request, 'results.html', {'my_object':my_object,'result':result,'pending':False,'my_msg':my_msg})
            
def autocomplete(request):
    sqs=SearchQuerySet()
    sqs1 = sqs.autocomplete(content_auto_name=request.GET.get('q', ''))[:5]
    sqs2 = sqs.autocomplete(content_auto_acc=request.GET.get('q', ''))[:5]    
    sqs3 = sqs.autocomplete(content_auto_taxname=request.GET.get('q', ''))[:5]
    sqs4 = sqs.autocomplete(content_auto_taxid=request.GET.get('q', ''))[:5]
    sqs5 = sqs.filter(text=request.GET.get('q', ''),django_ct='term_db.term')[:5]
    sqs6 = sqs.filter(text=request.GET.get('q', ''),django_ct='taxid_db.term')[:5]
    #sqs5 = sqs.filter(text=request.GET.get('q', ''),django_ct='term_db.term')[:5]	
    suggestions1 = [result.object.name for result in sqs5+sqs1+sqs2]	
    suggestions2 = [result.object.tax_name for result in sqs6+sqs3+sqs4]	
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
    if request.GET.get('my_search_field'):
        form = form_class(request.GET, searchqueryset=searchqueryset, load_all=load_all)

        if form.is_valid():
            query = form.cleaned_data['my_search_field']
            results = form.search()
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