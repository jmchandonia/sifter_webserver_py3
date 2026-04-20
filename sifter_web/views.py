from django.shortcuts import render
#from django.template import  Context
#from django.template.loader import get_template
from django import forms
from django.http import HttpResponseRedirect,HttpResponse,Http404
from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList
from sifter_web.fileops import resolve_runtime_artifact, safe_set_file_metadata
from sifter_web.tasks import run_sifter_job,run_sifter_job_domain
#from scripts.alk import find_results_domain
from results.models import SIFTER_Output
from sifter_results_ready_db.models import SifterResults as SifterResultsReady
from idmap_db.models import Idmap
import datetime
import logging
import random
import pickle
import os
import socket
import time
from types import SimpleNamespace
from urllib.parse import urlparse
from sifter_web.scripts.estimate_time import estimate_time, get_processing_time
from estimatedb.models import Errorhistogrambars
import numpy as np
from django.db.models import Q as Q_lookup
from haystack.query import SearchQuerySet
from haystack.forms import SearchForm
from haystack.query import EmptySearchQuerySet
from haystack.exceptions import SearchBackendError
from django.core.paginator import EmptyPage, InvalidPage, PageNotAnInteger, Paginator
from django.conf import settings
import json
from term_db.models import Term
from taxid_db.models import Taxid
from django.template import Context, loader
import re
from django.core.files import File 
from django.core.mail import send_mail

'''from sifter_results_db.models import SifterResults
import cPickle,zlib
from term_db.models import Term
from pfamdb.models import Pfam
import operator'''

RESULTS_PER_PAGE = getattr(settings, 'HAYSTACK_SEARCH_RESULTS_PER_PAGE', 50)
pred_results_per_page=1000
pred_results_per_page_sq=1
INPUT_DIR=getattr(settings, 'SIFTER_INPUT_DIR', os.path.join(os.path.dirname(__file__),"input"))
OUTPUT_DIR=getattr(settings, 'SIFTER_OUTPUT_DIR', os.path.join(os.path.dirname(__file__),"output"))
FILE_OWNER = getattr(settings, 'SIFTER_FILE_OWNER', None)
FILE_GROUP = getattr(settings, 'SIFTER_FILE_GROUP', None)
logger = logging.getLogger(__name__)
_SOLR_AVAILABLE = None


def pickle_dump_file(path, data):
    with open(path, 'wb') as handle:
        pickle.dump(data, handle)


def pickle_load_file(path):
    resolved_path = resolve_runtime_artifact(path, OUTPUT_DIR)
    with open(resolved_path, 'rb') as handle:
        try:
            return pickle.load(handle, encoding='latin1')
        except TypeError:
            return pickle.load(handle)


def resolve_output_artifact(path):
    return resolve_runtime_artifact(path, OUTPUT_DIR)


def safe_spelling_suggestion(results, search_form, query):
    try:
        if results.query.backend.include_spelling:
            return search_form.get_suggestion()
        return results.spelling_suggestion(query)
    except Exception:
        return None


def solr_available():
    global _SOLR_AVAILABLE
    if _SOLR_AVAILABLE is not None:
        return _SOLR_AVAILABLE
    if not getattr(settings, 'SIFTER_ENABLE_SOLR_SEARCH', True):
        _SOLR_AVAILABLE = False
        return _SOLR_AVAILABLE

    try:
        solr_url = settings.HAYSTACK_CONNECTIONS['default']['URL']
        parsed = urlparse(solr_url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        if not host:
            _SOLR_AVAILABLE = False
            return _SOLR_AVAILABLE
        with socket.create_connection((host, port), timeout=getattr(settings, 'SIFTER_SOLR_TIMEOUT', 1)):
            _SOLR_AVAILABLE = True
    except OSError:
        _SOLR_AVAILABLE = False
    return _SOLR_AVAILABLE


def wrap_term_result(term):
    return SimpleNamespace(object=term, acc=term.acc)


def wrap_taxid_result(taxid):
    return SimpleNamespace(object=taxid, taxid=taxid.tax_id, tax_id=taxid.tax_id)


def fallback_uniprot_results(query):
    q = query.strip().upper()
    direct_ids = set(SifterResultsReady.objects.filter(uniprot_id=q).values_list('uniprot_id', flat=True))
    mapped_ids = set(Idmap.objects.filter(other_id=q, db='ID').values_list('unip_id', flat=True))
    matches = sorted(direct_ids | mapped_ids)
    return [{'name': value, 'url': '/predictions/?protein=%s' % value} for value in matches]


def fallback_term_results(query, limit=None):
    q = query.strip()
    results = []
    seen = set()
    queryset = Term.objects.none()
    if q:
        queryset = Term.objects.filter(Q_lookup(acc__iexact=q) | Q_lookup(acc__istartswith=q) | Q_lookup(name__icontains=q)).order_by('acc')
    for term in queryset:
        if term.acc in seen:
            continue
        seen.add(term.acc)
        results.append(wrap_term_result(term))
        if limit and len(results) >= limit:
            break
    return results


def fallback_taxid_results(query, limit=None):
    q = query.strip()
    results = []
    seen = set()
    if not q:
        return results

    queryset = Taxid.objects.filter(
        Q_lookup(tax_name__icontains=q) |
        Q_lookup(short_name__icontains=q) |
        Q_lookup(tax_id__startswith=q)
    ).order_by('tax_name')
    if q.isdigit():
        queryset = Taxid.objects.filter(
            Q_lookup(tax_id=q) |
            Q_lookup(tax_name__icontains=q) |
            Q_lookup(short_name__icontains=q) |
            Q_lookup(tax_id__startswith=q)
        ).order_by('tax_name')

    for taxid in queryset:
        if taxid.tax_id in seen:
            continue
        seen.add(taxid.tax_id)
        results.append(wrap_taxid_result(taxid))
        if limit and len(results) >= limit:
            break
    return results


def fallback_search_results(query):
    return [
        {'model': 'Proteins', 'results': fallback_uniprot_results(query)},
        {'model': 'Species', 'results': fallback_taxid_results(query)},
        {'model': 'Functions', 'results': fallback_term_results(query)},
    ]


def search_with_solr_or_fallback(query):
    q = query.strip().upper()
    if not q:
        return fallback_search_results(q)

    if solr_available():
        try:
            sqs = SearchQuerySet()
            sqs1 = sqs.filter(content_auto_name=q)
            sqs2 = sqs.filter(content_auto_acc=q)
            sqs3 = sqs.filter(content_auto_taxname=q)
            sqs4 = sqs.filter(content_auto_taxid=q)
            sqs5 = sqs.filter(text=q)
            sqs = sqs5 | sqs1 | sqs2 | sqs3 | sqs4
            sqs_term = sqs.filter(django_ct='term_db.term')
            sqs_taxid = sqs.filter(django_ct='taxid_db.taxid')
            sqs_unip = fallback_uniprot_results(q)
            return [
                {'model': 'Proteins', 'results': sqs_unip},
                {'model': 'Species', 'results': sqs_taxid},
                {'model': 'Functions', 'results': sqs_term},
            ]
        except SearchBackendError:
            logger.warning("Solr search failed for %s; falling back to ORM search", q, exc_info=True)

    return fallback_search_results(q)


def fallback_species_option_results(query, function_query=''):
    results = []
    suffix = '&my_f=%s' % function_query if function_query else ''
    for taxid in fallback_taxid_results(query):
        if function_query:
            url = '/predictions/?sf-taxid=%s%s' % (taxid.taxid, suffix)
        else:
            url = '/predictions/?s-taxid=%s' % taxid.taxid
        results.append({'name': '%s (taxid:%s)' % (taxid.object.tax_name, taxid.taxid), 'url': url})
    return results


class InputForm(forms.Form):
    #input_any = forms.CharField(widget=forms.Textarea(attrs={'rows':1, 'placeholder':'Enter your queries','class':'form-control','id':'input_any'}),label='Input Any Queries', max_length=100000,required=False)
    input_queries = forms.CharField(widget=forms.Textarea(attrs={'rows':3, 'placeholder':'Enter query proteins','class':'form-control','id':'input_queries'}),label='Input Queries', max_length=100000,required=False)
    query_uploader = forms.FileField(widget=forms.FileInput(attrs={'id':'query_uploader'}),required=False)
    input_species = forms.CharField(widget=forms.TextInput(attrs={'placeholder':'Enter query species Taxonomy ID','class':'form-control','id':'input_species','autocomplete':'off'}),label='Input Species', max_length=1000,required=False)
    input_function = forms.CharField(widget=forms.Textarea(attrs={'rows':3, 'placeholder':'Enter query functions','class':'form-control','id':'input_function'}),label='Input Function', max_length=100000,required=False)
    function_uploader = forms.FileField(widget=forms.FileInput(attrs={'id':'function_uploader'}),required=False)
    input_function_sp = forms.CharField(widget=forms.TextInput(attrs={'placeholder':'Enter query functions','class':'form-control','id':'input_function_sp','autocomplete':'off'}),label='Input Function Sp', max_length=100000,required=False)
    input_sequence = forms.CharField(widget=forms.Textarea(attrs={'rows':10, 'placeholder':'Enter query sequences','class':'form-control','id':'input_sequence'}),label='Input Sequences', max_length=100000,required=False)
    sequence_uploader = forms.FileField(widget=forms.FileInput(attrs={'id':'sequence_uploader'}),required=False)
    input_email = forms.CharField(widget=forms.EmailInput(attrs={'id':'input_email','placeholder':'Enter email','class':'form-control',}),label='Input Email', max_length=100,required=False)
    sifter_choices = forms.ChoiceField(widget=forms.RadioSelect, choices=(('EXP-Model', 'Only use experimental evidence (SIFTER EXP-Model)',)
        , ('ALL-Model', 'Use both experimental and non-experimental evidence (SIFTER ALL-Model)',)),initial='EXP-Model',required=False)
    active_tab_hidden = forms.CharField(widget=forms.HiddenInput(attrs={'id':'active_tab_hidden'}),required=False)
    ExpWeight_hidden = forms.CharField(widget=forms.HiddenInput(attrs={'id':'ExpWeight_hidden'}),initial='0.7',required=False)
    more_options_hidden= forms.BooleanField(widget=forms.HiddenInput(attrs={'id':'more_options_hidden'}),initial=False,required=False)
    function_selected_hidden= forms.CharField(widget=forms.HiddenInput(attrs={'id':'function_selected_hidden'}),initial='',required=False)
    sp_selected_hidden= forms.CharField(widget=forms.HiddenInput(attrs={'id':'sp_selected_hidden'}),initial='',required=False)
    spf_selected_hidden= forms.CharField(widget=forms.HiddenInput(attrs={'id':'spf_selected_hidden'}),initial='',required=False)
    error_sp_hidden= forms.CharField(widget=forms.HiddenInput(attrs={'id':'error_sp_hidden'}),initial='',required=False)

    
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
            if not self.cleaned_data['sp_selected_hidden']:        
                self.check(cleaned_data,['input_species'],'Species IDs are not entered.')
        elif active_tab=='by_function':
            if not self.cleaned_data['function_selected_hidden']:
                self.check(cleaned_data,['input_function','function_sp_uploader'],'GO term IDs are not entered.')                
            if not self.cleaned_data['spf_selected_hidden']:
                self.check(cleaned_data,['input_function_sp','function_sp_uploader'],'Species IDs are not entered.')            
        elif active_tab=='by_sequence':
            self.check(cleaned_data,['input_sequence','sequence_uploader'],'Query sequences are not entered.')
            seq_data=cleaned_data.get('input_sequence')
            n_seq=seq_data.count('>')
            if n_seq==0 and len(seq_data)>0:
                self._errors['input_sequence'] = ErrorList(["Your inpur is in wrong format. Please use FASTA format input."])
            elif n_seq>10:
                self._errors['input_sequence'] = ErrorList(["You cannot entered more than 10 sequences."]) 
            elif len(seq_data)>1000000:
                self._errors['input_sequence'] = ErrorList(["You input sequences are too big."]) 
            else:
                lines=seq_data.split('\n')
                lines=[w.strip() for w in lines if w.strip()]
                lines=[w for w in lines if not w[0]=='>']            
                letters=set([v.lower() for w in lines for v in w])
                if len(letters)==4:
                    if len(letters|set(['a','c','g','t']))==4 or len(letters|set(['a','c','g','u']))==4:
                        self._errors['input_sequence'] = ErrorList(["You have entered NUCLEOTIDE sequences. Please enter your PROTEIN sequences."])
            
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
    q=forms.CharField(widget=forms.TextInput(attrs={'rows':1, 'placeholder':'Enter your queries','class':'form-control', 'autocomplete':'off'}),label='Input Any Queries', max_length=100000,required=True)
    def no_query_found(self):
        return self.searchqueryset.all()

    

    def search(self):
        if not self.is_valid():
            return self.no_query_found()

        if self.cleaned_data['q']:
            return search_with_solr_or_fallback(self.cleaned_data['q'])
        return fallback_search_results('')

class EstimateForm(forms.Form):
    estim_choices = forms.ChoiceField(widget=forms.RadioSelect, choices=(('params', 'Customized Input',),('pfam', 'Use a Pfam ID',)),initial='params')
    pfam = forms.CharField( label='PFAM ID', required=False)
    numTerms = forms.IntegerField(label='Number of candidate functions', required=False)
    famSize = forms.IntegerField(label='Family size', required=False)
    active_choice_hidden = forms.CharField(widget=forms.HiddenInput(attrs={'id':'active_choice_hidden'}),initial='params',required=False)    
    
    def set_default(self,field,value):
        data = self.data.copy()
        data[field] = value
        self.data = data


def show_help(request):
    return render(request, 'help.html')

def show_about(request):
    return render(request, 'about.html')

def show_download(request):
    return render(request, 'download.html')

def show_contact(request):
    return render(request, 'contact.html')

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
            #active_choice=form.cleaned_data['active_choice_hidden']
            #form.set_default('active_choice_hidden',active_choice)
            choices = form.cleaned_data['estim_choices']
            form.set_default('estim_choices',choices)
            
            if choices=='pfam':
                form.fields['numTerms'].widget.attrs['disabled'] = 'True'
                form.fields['famSize'].widget.attrs['disabled'] = 'True'
            else:
                form.fields['pfam'].widget.attrs['disabled'] = 'True'
            

            

            if choices == 'pfam':
                pfam = form.cleaned_data['pfam']
                if not pfam:
                    return render_error('Please enter a PFAM ID')
                (tableHeader, tableBody, histograms, chartContainers, numTerms,famSize) = get_processing_time(pfam)
                if not tableHeader:
                    return render_error('Error: PFAM ID %s is not in the database' % pfam)
                else:
                    form.set_default('numTerms',numTerms)
                    form.set_default('famSize',famSize)
                    
            else:
                numTerms = form.cleaned_data['numTerms']
                famSize = form.cleaned_data['famSize']
                if not numTerms or numTerms < 0:
                    return render_error('Please enter a positive integer for the number of GO terms')
                elif not famSize or famSize < 0:
                    return render_error('Please enter a positive integer for the family size')
                (tableHeader, tableBody, histograms, chartContainers, numTerms,famSize) = estimate_time(numTerms, famSize)
            if not histograms:
                return render(request, 'complexity.html', {'form': form,
                    'tableHeader': tableHeader, 'tableBody': tableBody, 'displayHist': False})                
            return render(request, 'complexity.html',
                {'form': form, 'tableHeader': tableHeader, 'tableBody': tableBody, 'histograms': histograms,
                'displayHist': True, 'chartContainers': chartContainers, 'numTerms': numTerms})
        else:
            return render(request, 'complexity.html',
                {'form': form, 'response': 'Error'})

    # if a GET (or any other method) we'll create a blank form
    else:
        form = EstimateForm()
        form.fields['pfam'].widget.attrs['disabled'] = 'True'
        return render(request, 'complexity.html', {'form': form,})

def delete_old_results():
    olddate = datetime.date.today()+datetime.timedelta(days=-15)
    old_job_ids=SIFTER_Output.objects.filter(result_date__lte=olddate).values_list('job_id',flat=True)
    for job_id in old_job_ids:
        infile=os.path.join(INPUT_DIR,"%s_input.pickle"%job_id)
        if os.path.exists(infile):
            os.remove(infile)
        outfile=os.path.join(OUTPUT_DIR,"%s_output.pickle"%job_id)
        if os.path.exists(outfile):
            os.remove(outfile)
        outfile=os.path.join(OUTPUT_DIR,"%s_download.txt"%job_id)
        if os.path.exists(outfile):
            os.remove(outfile)
        outfile=os.path.join(OUTPUT_DIR,"%s_nopreds.txt"%job_id)
        if os.path.exists(outfile):
            os.remove(outfile)
        outfile=os.path.join(OUTPUT_DIR,"%s_output.blast"%job_id)
        if os.path.exists(outfile):
            os.remove(outfile)
        outfile=os.path.join(OUTPUT_DIR,"%s_output.blast.msg"%job_id)
        if os.path.exists(outfile):
            os.remove(outfile)
    
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
    

def get_input(request,context={}):
    
    if context:
        return render(request, 'home.html', context)
        
    searchqueryset=None
    load_all=True
    extra_context=None
    results_per_page=None
    query = ''
    results = EmptySearchQuerySet()
    search_form = MySearchForm(searchqueryset=searchqueryset, load_all=load_all)
    pages = ''
    paginators=''
    ip=get_client_ip(request)
    context = {
        'search_form': search_form,
        'pages': pages,
        'paginators': paginators,
        'query': query,
        'suggestion': None,
    }
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
                return render(request, 'home.html', context)
            else:
                job_id=random.randint(1000000,9999999)
                while SIFTER_Output.objects.filter(job_id=job_id):
                    job_id=random.randint(1000000,9999999)
                
                infile=os.path.join(INPUT_DIR,"%s_input.pickle"%job_id)
                my_species=0
                my_functions=[]
                my_proteins=[]
                n_sequences=0
                if active_tab=='by_protein':                
                    splited=re.split(' |,|;|\n',form.cleaned_data['input_queries'].strip())
                    my_proteins=list(set([w.strip().upper() for w in splited if w]))
                    data={'proteins':my_proteins}
                elif active_tab=='by_species':
                    if not form.cleaned_data['sp_selected_hidden']:
                        my_species=form.cleaned_data['input_species'].strip()
                        if my_species:
                            return HttpResponseRedirect('/search_options/?q=%s'%my_species)                            
                    else:
                        my_species=form.cleaned_data['sp_selected_hidden']
                    data={'species':my_species}
                elif active_tab=='by_function':
                    if not form.cleaned_data['function_selected_hidden']:
                        splited=re.split(' |,|;\n',form.cleaned_data['input_function'].strip())
                        my_functions=list(set([w for w in splited if w]))
                    else:
                        splited=re.split(' |,|;\n',form.cleaned_data['function_selected_hidden'])
                        my_functions=list(set([w for w in splited if w]))
                
                    if not form.cleaned_data['spf_selected_hidden']:
                        my_species=form.cleaned_data['input_function_sp'].strip()
                        if my_species:
                            if my_functions:
                                my_functions_string='&my_f='+','.join(my_functions)
                            else:
                                my_functions_string=''
                            return HttpResponseRedirect('/search_options/?fq=%s%s'%(my_species,my_functions_string))                                                        
                    else:
                        my_species=form.cleaned_data['spf_selected_hidden']

                    data={'species':my_species,'functions':my_functions}                
                elif active_tab=='by_sequence':
                    my_sequences=form.cleaned_data['input_sequence']
                    n_sequences=my_sequences.count('>')
                    data={'sequences':my_sequences}                
                    same_ip_today_seq=SIFTER_Output.objects.filter(result_date=datetime.date.today(),ip=ip,query_method='by_sequence').values_list('job_id',flat=True)
                    logger.info("Sequence submission count for %s is %s before job %s", ip, len(same_ip_today_seq), job_id)
                    if len(same_ip_today_seq)>20:
                        context['form']=form
                        context['response']=form.cleaned_data['ExpWeight_hidden']        
                        context['error_same_ip_sq']="You can only submit upto 20 'Search by Sequences' requests (each with upto 10 sequences) from a same IP in a same day. "
                        return render(request, 'home.html', context)
                    
                    
                pickle_dump_file(infile, data)
                safe_set_file_metadata(infile, mode=0o775, user=FILE_OWNER, group=FILE_GROUP)
                P=SIFTER_Output(job_id=job_id,exp_weight=form.cleaned_data['ExpWeight_hidden'], email = form.cleaned_data['input_email'],
                                query_method=active_tab, sifter_EXP_choices = True if sifter_choices_val=='EXP-Model' else False,
                                n_proteins=len(my_proteins),species=my_species,n_functions=len(my_functions),n_sequences=n_sequences,submission_date=datetime.date.today(),
                                result_date=datetime.date.today(),input_file=infile,output_file='',deleted=False,ip=ip)
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
            function_selected_hidden=form.cleaned_data['function_selected_hidden']
            form.fields['function_selected_hidden'].widget.attrs['value']=function_selected_hidden
            spf_selected_hidden=form.cleaned_data['spf_selected_hidden']
            form.fields['spf_selected_hidden'].widget.attrs['value']=spf_selected_hidden
            sp_selected_hidden=form.cleaned_data['sp_selected_hidden']
            form.fields['sp_selected_hidden'].widget.attrs['value']=sp_selected_hidden
            error_sp_hidden=form.cleaned_data['error_sp_hidden']
            form.fields['error_sp_hidden'].widget.attrs['value']=error_sp_hidden
            
            if function_selected_hidden:
                my_functions_string=function_selected_hidden
                my_functions=my_functions_string.split(',')                
                if len(my_functions)==1:
                    my_function=my_functions[0]
                    term=Term.objects.filter(acc=my_function).values('name','acc')
                    if term:
                        term=term[0]
                        context['function_selected']='%s (%s)'%(term['name'],term['acc'])
                    else:
                        context['function_selected']=my_function
                else:
                    context['function_selected']=my_functions_string
            
            context['form']=form
            context['response']=form.cleaned_data['ExpWeight_hidden']        

            return render(request, 'home.html', context)

    # if a GET (or any other method) we'll create a blank form
    else:
        if request.GET.get('q'):    
            #search form processing
            search_form = MySearchForm(request.GET, searchqueryset=searchqueryset, load_all=load_all)
            if search_form.is_valid():
                query = search_form.cleaned_data['q']
                results = search_form.search()
        else:
            search_form = MySearchForm(searchqueryset=searchqueryset, load_all=load_all)
        
        if results:
            if len(results[0]['results'])==0 and len(results[1]['results'])==0 and len(results[2]['results'])==1:                            
                return HttpResponseRedirect('/predictions/?term=%s'%results[2]['results'][0].acc)
            elif len(results[0]['results'])==0 and len(results[1]['results'])==1 and len(results[2]['results'])==0:                            
                return HttpResponseRedirect('/predictions/?taxid=%s'%results[1]['results'][0].taxid)
            if len(results[0]['results'])==1 and len(results[1]['results'])==0 and len(results[2]['results'])==0:                            
                return HttpResponseRedirect('/predictions/?protein=%s'%results[0]['results'][0]['name'])
        
        
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
            'suggestion': safe_spelling_suggestion(results, search_form, query) if query else None,
        }
        '''for result in results:
            if result['results'].query.backend.include_spelling:
                context['suggestion'] = search_form.get_suggestion()
            spelling = result['results'].spelling_suggestion(query)
            context['suggestion']= spelling'''
        
        if extra_context:
            context.update(extra_context)
        
        #other form processing    
        form = InputForm()
        form.fields['active_tab_hidden'].widget.attrs['value'] = 'by_any'
        context['form']=form
        context['response']='Hi'
        context['no_results']=False
        if results:
            if len(results[0]['results'])==0 and len(results[1]['results'])==0 and len(results[2]['results'])==0:
                context['no_results']=True
        return render(request, 'home.html', context)
        

    #return render(request, 'home.html', context)

def show_search_options(request):
    results_per_page=None
    qdict=dict(request.GET.lists())
    fq_flag=0
    if ('q' in qdict) or ('fq' in qdict):
        if 'q' in qdict:
            my_species=qdict['q'][0]
        else:
            my_species=qdict['fq'][0]
            fq_flag=1
            if 'my_f' in qdict:
                my_functions_string='&my_f='+qdict['my_f'][0]
            else:
                my_functions_string=''
        
        if my_species.isdigit():
            sqs0=list(set(Taxid.objects.filter(tax_id=my_species).values_list('tax_id',flat=True)))
            if sqs0:
                tid=my_species
                if fq_flag==0:
                      return HttpResponseRedirect('/predictions/?s-taxid=%s'%tid, {'results':''})
                else:
                      return HttpResponseRedirect('/predictions/?sf-taxid=%s%s'%(tid,my_functions_string), {'results':''})
        sqs_taxid = fallback_taxid_results(my_species)
        if solr_available():
            try:
                sqs = SearchQuerySet()
                sqs3 = sqs.filter(content_auto_taxname=my_species)
                sqs4 = sqs.filter(content_auto_taxid=my_species)
                sqs5 = sqs.filter(text=my_species)
                sqs = sqs3 | sqs4 | sqs5
                sqs_taxid = sqs.filter(django_ct='taxid_db.taxid')
            except SearchBackendError:
                logger.warning("Solr species search failed for %s; using ORM fallback", my_species, exc_info=True)
        if len(sqs_taxid)>1:
            context_search={}
            if fq_flag==0:
                sqs_sp_results=[{'model':'Species','results':[{'name':'%s (taxid:%s)'%(w.object.tax_name,w.object.tax_id), 'url':'/predictions/?s-taxid=%s' % w.object.tax_id} for w in sqs_taxid]}]
            else:
                sqs_sp_results=[{'model':'Species','results':[{'name':'%s (taxid:%s)'%(w.object.tax_name,w.object.tax_id), 'url':'/predictions/?sf-taxid=%s%s' % (w.object.tax_id,my_functions_string)} for w in sqs_taxid]}]                                                
            
            context_search['sqs_sp_results']=sqs_sp_results
            paginators=[]
            pages=[]
            for i,result in enumerate(sqs_sp_results):
                paginator=Paginator(result['results'], results_per_page or RESULTS_PER_PAGE)
                paginators.append(paginator)
                try:
                    pages.append({'model':result['model'],'page':paginator.page(int(request.GET.get('page', 1)))})
                except InvalidPage:
                    raise Http404("No such page of results!")
                
            context_search['pages']= pages
            context_search['paginators']= paginators
            context_search['query']= my_species
            #return HttpResponseRedirect('/search_options/?sp=%s'%my_species,context_search)                                
            return render(request, 'search_options.html', context_search)
        elif len(sqs_taxid)==1:
            tid=sqs_taxid[0].object.tax_id
            if fq_flag==0:
                  return HttpResponseRedirect('/predictions/?s-taxid=%s'%tid, {'results':''})
            else:
                  return HttpResponseRedirect('/predictions/?sf-taxid=%s%s'%(tid,my_functions_string), {'results':''})
        else:
            form = InputForm()
            if fq_flag==0:
                form.fields['active_tab_hidden'].widget.attrs['value'] = 'by_species'
            else:
                form.fields['active_tab_hidden'].widget.attrs['value'] = 'by_function'
            context={}
            context['form']=form
            context['response']='Hi'
            form.fields['error_sp_hidden'].widget.attrs['value']='1'
            return render(request, 'home.html', context)
            
    



def show_results(request,job_id):
    time.sleep(0.5)
    my_object=SIFTER_Output.objects.filter(job_id=job_id)
    my_msg=[]
    if not len(my_object)==1:
        my_msg.append(['danger','Error in the job_id. Number of hits=%s'%(len(my_object))])       
        return render(request, 'results.html', {'my_object':'','result':'','pending':False,'my_msg':my_msg,'species':'','nopreds':'','downloadfile':'','blast_error':''})
    my_object=my_object[0]
    species=Taxid.objects.filter(tax_id=my_object.species)
    if species:
        species=species[0]
        
    if my_object.output_file=='':
        my_msg.append(['warning','Thanks! You have successfully submitted your SIFTER query.'])
        if my_object.query_method == 'by_sequence':
            my_msg.append(['warning','We are trying to connet to the NCBI-BLAST server.'])
        my_blast_msg_file_path=OUTPUT_DIR+"/%s_output.blast.msg"%job_id
        if os.path.exists(my_blast_msg_file_path):
            read_file = open(my_blast_msg_file_path, "r")
            line=read_file.readline()
            my_msg.append(['warning',line])
        return render(request, 'results.html', {'my_object':my_object,'result':'','pending':False,'my_msg':my_msg,'species':species,'nopreds':'','downloadfile':'','blast_error':''})        
    else:
        output_file = resolve_output_artifact(my_object.output_file)
        if not os.path.exists(output_file):
            my_msg.append(['danger', 'Historical result artifact is missing from the migrated output directory.'])
            return render(request, 'results.html', {'my_object':my_object,'result':'','pending':False,'my_msg':my_msg,'species':species,'nopreds':'','downloadfile':'','blast_error':''})
        results=pickle_load_file(output_file)
        if 'bad_blast' in results:
            my_msg.append(['danger','BLAST server has been busy for the last 10 hours. We cannot process your query now. Please submit your query again later.'])
            return render(request, 'results.html', {'my_object':my_object,'result':'','pending':False,'my_msg':my_msg,'species':'','nopreds':'','downloadfile':'','blast_error':'1'})
        
        my_msg.append(['info','Your SIFTER query results are ready.'])
        nopreds=''
        downloadfile=''
        if 'nopreds' in results:
            nopreds=['/downloads/%s_nopreds.txt'%job_id,results['nopreds'][1]]
            
        if  'downloadfile' in results:
            downloadfile='/downloads/%s_download.txt'%job_id
        
        if not my_object.query_method =='by_sequence':
            paginator = Paginator(results['result'], pred_results_per_page)
            try:
                page = paginator.page(int(request.GET.get('page', 1)))
            except PageNotAnInteger:
                # If page is not an integer, deliver first page.
                page = paginator.page(1)
            except EmptyPage:
                page = paginator.page(paginator.num_pages)
            return render(request, 'results.html', {'my_object':my_object,'result':page,'pending':False,'my_msg':my_msg,'species':species,'nopreds':nopreds,'downloadfile':downloadfile,'blast_error':''})
        else:            
            paginator = Paginator(results['result'], pred_results_per_page_sq)
            try:
                page = paginator.page(int(request.GET.get('page', 1)))
            except PageNotAnInteger:
                # If page is not an integer, deliver first page.
                page = paginator.page(1)
            except EmptyPage:
                page = paginator.page(paginator.num_pages)
            return render(request, 'results.html', {'my_object':my_object,'result':page,'pending':False,'my_msg':my_msg,'species':species,'nopreds':nopreds,'downloadfile':downloadfile,'blast_error':''})
          
            
        

def show_predictions(request):
    ip=get_client_ip(request)
    qdict=dict(request.GET.lists())
    if 'term' in qdict:
        my_function=qdict['term'][0]
        form = InputForm()
        form.fields['active_tab_hidden'].widget.attrs['value'] = 'by_function'
        form.fields['function_selected_hidden'].widget.attrs['value'] = my_function
        context={}
        context['form']=form
        context['response']='Hi'
        term=Term.objects.filter(acc=my_function).values('name','acc')[0]
        context['function_selected']='%s (%s)'%(term['name'],term['acc'])
        return render(request, 'home.html', context)
        
    elif 'taxid' in qdict:
        job_id=random.randint(1000000,9999999)    
        while SIFTER_Output.objects.filter(job_id=job_id):
            job_id=random.randint(1000000,9999999)
        
        infile=os.path.join(INPUT_DIR,"%s_input.pickle"%job_id)
        my_species=qdict['taxid'][0]
        data={'species':my_species}
        pickle_dump_file(infile, data)
        safe_set_file_metadata(infile, mode=0o775, user=FILE_OWNER, group=FILE_GROUP)
        P=SIFTER_Output(job_id=job_id,exp_weight='0.7', email = '',
                        query_method='by_species', sifter_EXP_choices = True ,
                        n_proteins=0,species=my_species,n_functions=0,n_sequences=0,submission_date=datetime.date.today(),
                        result_date=datetime.date.today(),input_file=infile,output_file='',deleted=False,ip=ip)
        P.save()
        delete_old_results()
        my_form_data={'sifter_choices':'EXP-Model','ExpWeight_hidden':'0.7'
        ,'active_tab_hidden':'by_species'}

        run_sifter_job.delay(my_form_data,job_id)
        return HttpResponseRedirect('/results-id=%s'%job_id, {'results':''})
    elif 'protein' in qdict:
        job_id=random.randint(1000000,9999999)    
        while SIFTER_Output.objects.filter(job_id=job_id):
            job_id=random.randint(1000000,9999999)
        infile=os.path.join(INPUT_DIR,"%s_input.pickle"%job_id)
        my_proteins=[qdict['protein'][0]] 
        data={'proteins':my_proteins}
        pickle_dump_file(infile, data)
        safe_set_file_metadata(infile, mode=0o775, user=FILE_OWNER, group=FILE_GROUP)
        P=SIFTER_Output(job_id=job_id,exp_weight='0.7', email = '',
                        query_method='by_protein', sifter_EXP_choices = True ,
                        n_proteins=1,species=0,n_functions=0,n_sequences=0,submission_date=datetime.date.today(),
                        result_date=datetime.date.today(),input_file=infile,output_file='',deleted=False,ip=ip)
        P.save()
        delete_old_results()
        my_form_data={'sifter_choices':'EXP-Model','ExpWeight_hidden':'0.7'
        ,'active_tab_hidden':'by_protein'}

        run_sifter_job.delay(my_form_data,job_id)
        return HttpResponseRedirect('/results-id=%s'%job_id, {'results':''})        
    elif 's-taxid' in qdict:
        my_species=qdict['s-taxid'][0]
        form = InputForm()
        form.fields['active_tab_hidden'].widget.attrs['value'] = 'by_species'
        form.fields['sp_selected_hidden'].widget.attrs['value'] = my_species
        context={}
        context['form']=form
        context['response']='Hi'
        taxid=Taxid.objects.filter(tax_id=my_species).values('tax_name','tax_id')[0]
        context['sp_selected']='%s (%s)'%(taxid['tax_name'],taxid['tax_id'])
        return render(request, 'home.html', context)
    elif 'sf-taxid' in qdict:
        my_species=qdict['sf-taxid'][0]
        form = InputForm()
        form.fields['active_tab_hidden'].widget.attrs['value'] = 'by_function'
        form.fields['spf_selected_hidden'].widget.attrs['value'] = my_species
        context={}
        if 'my_f' in qdict:
            my_functions_string=qdict['my_f'][0]
            if my_functions_string:
                my_functions=my_functions_string.split(',')                
                if len(my_functions)==1:
                    my_function=my_functions[0]
                    term=Term.objects.filter(acc=my_function).values('name','acc')
                    if term:
                        term=term[0]
                        form.fields['function_selected_hidden'].widget.attrs['value']=term['acc']
                        context['function_selected']='%s (%s)'%(term['name'],term['acc'])
                    else:
                        form.fields['function_selected_hidden'].widget.attrs['value']=my_function
                        context['function_selected']=my_function
                else:
                    form.fields['function_selected_hidden'].widget.attrs['value']=my_functions_string
                    context['function_selected']=my_functions_string
        context['form']=form
        context['response']='Hi'
        taxid=Taxid.objects.filter(tax_id=my_species).values('tax_name','tax_id')[0]
        context['spf_selected']='%s (%s)'%(taxid['tax_name'],taxid['tax_id'])
        return render(request, 'home.html', context)

def autocomplete(request):
    dbs=request.GET.get('dbs', '')
    if dbs=='all':
        search_in=['term','taxid','unip']
    else:
        search_in=[dbs]
    query = request.GET.get('q', '').strip()
    suggestions=[]

    if solr_available():
        try:
            sqs=SearchQuerySet()
            if 'term' in search_in:
                sqs1 = sqs.autocomplete(content_auto_name=query)[:5]
                sqs2 = sqs.autocomplete(content_auto_acc=query)[:5]
                sqs5 = sqs.filter(text=query,django_ct='term_db.term')[:5]
                suggestions.extend([{'url':result.object.get_absolute_url(),'label':"%s (%s)"%(result.object.name,result.object.acc)} for result in sqs5+sqs1+sqs2])
            if 'taxid' in search_in:
                sqs3 = sqs.autocomplete(content_auto_taxname=query)[:5]
                sqs4 = sqs.autocomplete(content_auto_taxid=query)[:5]
                sqs6 = sqs.filter(text=query,django_ct='taxid_db.taxid')[:5]
                suggestions.extend([{'url':result.object.get_absolute_url(),'label':"%s (taxid:%s)"%(result.object.tax_name,result.object.tax_id)} for result in sqs6+sqs3+sqs4])
        except SearchBackendError:
            logger.warning("Solr autocomplete failed for %s; using ORM fallback", query, exc_info=True)

    if 'term' in search_in and not suggestions:
        suggestions.extend([{'url': result.object.get_absolute_url(), 'label': "%s (%s)" % (result.object.name, result.object.acc)} for result in fallback_term_results(query, limit=5)])
    if 'taxid' in search_in and not [item for item in suggestions if 'taxid:' in item['label']]:
        suggestions.extend([{'url': result.object.get_absolute_url(), 'label': "%s (taxid:%s)" % (result.object.tax_name, result.object.tax_id)} for result in fallback_taxid_results(query, limit=5)])
    if 'unip' in search_in:
        if len(query)>7:
            sqs7=list(set(SifterResultsReady.objects.filter(uniprot_id=query).values_list('uniprot_id',flat=True)))
            suggestions.extend([{'url':'/predictions/?protein=%s'%w,'label':w} for w in sqs7])
    # Make sure you return a JSON object, not a bare list.
    # Otherwise, you could be vulnerable to an XSS attack.
    the_data = json.dumps({
        'results': suggestions
    })
    return HttpResponse(the_data, content_type='application/json')



def show_domain_predictions(request,job_id,my_protein):
    my_msg=[]
    my_object=SIFTER_Output.objects.filter(job_id=job_id)
    if not len(my_object)==1:
        my_msg.append(['danger','Error in the job_id. Number of hits=%s'%(len(my_object))])       
        return render(request, 'domain_preds.html', {'protein':'','domian_result':'','uniprot_acc':'','main_res':'','my_msg':my_msg})
    my_object=my_object[0]
    output_file = resolve_output_artifact(my_object.output_file)
    if not os.path.exists(output_file):
        my_msg.append(['danger','Historical result artifact is missing from the migrated output directory.'])
        return render(request, 'domain_preds.html', {'protein':'','domian_result':'','uniprot_acc':'','main_res':'','my_msg':my_msg})
    main_res0=pickle_load_file(output_file)['result']
    main_res=[]
    if not my_object.query_method=='by_sequence':
        for w in main_res0:
            if w[0]==my_protein:
                main_res=w
                break
        if not main_res:
            my_msg.append(['danger','No results for this protein in your query.'])       
            return render(request, 'domain_preds.html', {'protein':'','domian_result':'','uniprot_acc':'','main_res':'','my_msg':my_msg})
    else:
        for ww in main_res0:
            for w in ww[1]:
                if w[0]==my_protein:
                    main_res=[w[0],w[1],w[2],w[3],w[8]]
                    break
            if main_res:
                break
        if not main_res:
            my_msg.append(['danger','No results for this protein in your query.'])       
            return render(request, 'domain_preds.html', {'protein':'','domian_result':'','uniprot_acc':'','main_res':'','my_msg':my_msg})
    
    res,uniprot_acc=run_sifter_job_domain(my_protein,my_object.sifter_EXP_choices,float(my_object.exp_weight))
    return render(request, 'domain_preds.html', {'protein':my_protein,'domain_result':res,'uniprot_acc':uniprot_acc,'main_res':main_res,'my_msg':my_msg})
