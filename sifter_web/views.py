from django.shortcuts import render,render_to_response,RequestContext
#from django.template import  Context
#from django.template.loader import get_template
from django import forms
from django.http import HttpResponseRedirect,HttpResponse,Http404
from django.core.exceptions import ValidationError
from django.forms.util import ErrorList
from sifter_web.tasks import run_sifter_job
from results.models import SIFTER_Output
from sifter_results_ready_db.models import SifterResults as SifterResultsReady
from idmap_db.models import Idmap
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
from haystack.query import SearchQuerySet
from haystack.forms import SearchForm
from haystack.query import EmptySearchQuerySet
from django.core.paginator import Paginator, InvalidPage
from django.conf import settings
import json
from term_db.models import Term
from taxid_db.models import Taxid
from django.template import Context, loader
import re
from django.core.files import File 
from django.core.mail import send_mail

RESULTS_PER_PAGE = getattr(settings, 'HAYSTACK_SEARCH_RESULTS_PER_PAGE', 50)
pred_results_per_page=1000
pred_results_per_page_sq=1
INPUT_DIR=os.path.join(os.path.dirname(__file__),"input")
OUTPUT_DIR=os.path.join(os.path.dirname(__file__),"output")


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
        # First, store the SearchQuerySet received from other processing.
        sqs = SearchQuerySet()

        if not self.is_valid():
            return self.no_query_found()

        # Check to see if a q was chosen.
        if self.cleaned_data['q']:        
            q=self.cleaned_data['q'].strip()
            if q:
                sqs1 = sqs.filter(content_auto_name=q)
                sqs2 = sqs.filter(content_auto_acc=q)            
                sqs3 = sqs.filter(content_auto_taxname=q)
                sqs4 = sqs.filter(content_auto_taxid=q)
                sqs5 = sqs.filter(text=q)
                sqs=sqs5|sqs1|sqs2|sqs3|sqs4
                sqs_term=sqs.filter(django_ct='term_db.term')            
                sqs_taxid=sqs.filter(django_ct='taxid_db.taxid')
                sqs7=list(set(SifterResultsReady.objects.filter(uniprot_id=q).values_list('uniprot_id',flat=True)))
                #sqs8=list(set(SifterResultsReady.objects.filter(uniprot_acc=q).values_list('uniprot_id',flat=True)))
                sqs8=Idmap.objects.filter(other_id=q, db='ID').values_list('unip_id',flat=True)
                sqs_unip=list(set(sqs8)|set(sqs7))
                sqs_unip=[{'name':w, 'url':'/predictions/?protein=%s' % w} for w in sqs_unip]
        return [{'model':'Proteins','results':sqs_unip},{'model':'Species','results':sqs_taxid},{'model':'Functions','results':sqs_term}]

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
                    return render_error('Error: PFAM id %s is not in the database' % pfam)
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
    
    

def get_input(request,context={}):
    
    if context:
        return render_to_response('home.html', context, context_instance=context_class(request))
        
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
                
                infile=os.path.join(INPUT_DIR,"%s_input.pickle"%job_id)
                my_species=0
                my_functions=[]
                my_proteins=[]
                n_sequences=0
                if active_tab=='by_protein':
                    splited=re.split(' |,|;|\n',form.cleaned_data['input_queries'].strip())
                    my_proteins=list(set([w.strip() for w in splited if w]))
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
                pickle.dump(data,open(infile,'w'))
                os.system("chmod 775 %s"%infile)
                os.system("chgrp sifter-group %s"%infile)
                P=SIFTER_Output(job_id=job_id,exp_weight=form.cleaned_data['ExpWeight_hidden'], email = form.cleaned_data['input_email'],
                                query_method=active_tab, sifter_EXP_choices = True if sifter_choices_val=='EXP-Model' else False,
                                n_proteins=len(my_proteins),species=my_species,n_functions=len(my_functions),n_sequences=n_sequences,submission_date=datetime.date.today(),
                                result_date=datetime.date.today(),input_file=infile,output_file='',deleted=False)
                P.save()
                delete_old_results()
                my_form_data={'sifter_choices':form.cleaned_data['sifter_choices'],'ExpWeight_hidden':form.cleaned_data['ExpWeight_hidden']
                              ,'active_tab_hidden':form.cleaned_data['active_tab_hidden']}
                '''msg='results in: http://sifter.berkeley.edu/results-id=%s\n'%job_id
                msg+='Job submitted on: %s\n'%datetime.date.today()
                msg+='query_method: %s\n'%active_tab
                msg+='SIFTER choice: %s\n'%sifter_choices_val
                msg+='EXP Weight: %s\n'%form.cleaned_data['ExpWeight_hidden']
                msg+='Number of proteins: %s\n'%len(my_proteins)
                msg+='Species: %s\n'%(my_species)
                msg+='Number of functions: %s\n'%len(my_functions)
                msg+='Number of sequences: %s\n'%(n_sequences)
                send_mail('SIFTER-WEB run for Job ID:%s\n'%job_id, msg, 'sifter@compbio.berkeley.edu',['sahraeian.m@gmail.com'], fail_silently=False)'''
                
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

            return render_to_response('home.html', context, context_instance=context_class(request))        

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
            'suggestion': None,
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
        return render_to_response('home.html', context, context_instance=context_class(request))        
        

    #return render(request, 'home.html', context)

def show_search_options(request):
    results_per_page=None
    context_class=RequestContext        

    qdict=dict(request.GET.iterlists())
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
        sqs = SearchQuerySet()
        sqs3 = sqs.filter(content_auto_taxname=my_species)
        sqs4 = sqs.filter(content_auto_taxid=my_species)
        sqs5 = sqs.filter(text=my_species)
        sqs=sqs3|sqs4|sqs5
        sqs_taxid=sqs.filter(django_ct='taxid_db.taxid')
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
            return render_to_response('search_options.html', context_search, context_instance=context_class(request))
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
            context_class=RequestContext        
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
        return render(request, 'results.html', {'my_object':'','result':'','pending':False,'my_msg':my_msg,'species':'','nopreds':'','downloadfile':''})
    my_object=my_object[0]
    species=Taxid.objects.filter(tax_id=my_object.species)
    if species:
        species=species[0]
        
    if my_object.output_file=='':
        my_msg.append(['warning','Thanks! You have successfully submitted your SIFTER query.'])
        return render(request, 'results.html', {'my_object':my_object,'result':'','pending':False,'my_msg':my_msg,'species':species,'nopreds':'','downloadfile':''})        
    else:
        my_msg.append(['info','Your SIFTER query results are ready.'])
        results=pickle.load(open(my_object.output_file))
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
            return render(request, 'results.html', {'my_object':my_object,'result':page,'pending':False,'my_msg':my_msg,'species':species,'nopreds':nopreds,'downloadfile':downloadfile})
        else:            
            paginator = Paginator(results['result'], pred_results_per_page_sq)
            try:
                page = paginator.page(int(request.GET.get('page', 1)))
            except PageNotAnInteger:
                # If page is not an integer, deliver first page.
                page = paginator.page(1)
            except EmptyPage:
                page = paginator.page(paginator.num_pages)
            return render(request, 'results.html', {'my_object':my_object,'result':page,'pending':False,'my_msg':my_msg,'species':species,'nopreds':nopreds,'downloadfile':downloadfile})
          
            
        

def show_predictions(request):
    qdict=dict(request.GET.iterlists())
    if 'term' in qdict:
        my_function=qdict['term'][0]
        form = InputForm()
        form.fields['active_tab_hidden'].widget.attrs['value'] = 'by_function'
        form.fields['function_selected_hidden'].widget.attrs['value'] = my_function
        context={}
        context_class=RequestContext        
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
        pickle.dump(data,open(infile,'w'))
        os.system("chmod 775 %s"%infile)
        os.system("chgrp sifter-group %s"%infile)
        P=SIFTER_Output(job_id=job_id,exp_weight='0.7', email = '',
                        query_method='by_species', sifter_EXP_choices = True ,
                        n_proteins=0,species=my_species,n_functions=0,n_sequences=0,submission_date=datetime.date.today(),
                        result_date=datetime.date.today(),input_file=infile,output_file='')
        P.save()
        delete_old_results()
        my_form_data={'sifter_choices':'EXP-Model','ExpWeight_hidden':'0.7'
        ,'active_tab_hidden':'by_species'}

        '''msg='results in: http://sifter.berkeley.edu/results-id=%s\n'%job_id
        msg+='Job submitted on: %s\n'%datetime.date.today()
        msg+='query_method: %s\n'%'by_species'
        msg+='SIFTER choice: %s\n'%'EXP-Model'
        msg+='EXP Weight: %s\n'%0.7
        msg+='Number of proteins: %s\n'%0
        msg+='Species: %s\n'%(my_species)
        msg+='Number of functions: %s\n'%0
        msg+='Number of sequences: %s\n'%0
        send_mail('SIFTER-WEB run for Job ID:%s\n'%job_id, msg, 'sifter@compbio.berkeley.edu',['sahraeian.m@gmail.com'], fail_silently=False)'''
        run_sifter_job.delay(my_form_data,job_id)
        return HttpResponseRedirect('/results-id=%s'%job_id, {'results':''})
    elif 'protein' in qdict:
        job_id=random.randint(1000000,9999999)    
        while SIFTER_Output.objects.filter(job_id=job_id):
            job_id=random.randint(1000000,9999999)
        infile=os.path.join(INPUT_DIR,"%s_input.pickle"%job_id)
        my_proteins=[qdict['protein'][0]] 
        data={'proteins':my_proteins}
        pickle.dump(data,open(infile,'w'))
        os.system("chmod 775 %s"%infile)
        os.system("chgrp sifter-group %s"%infile)
        P=SIFTER_Output(job_id=job_id,exp_weight='0.7', email = '',
                        query_method='by_protein', sifter_EXP_choices = True ,
                        n_proteins=1,species=0,n_functions=0,n_sequences=0,submission_date=datetime.date.today(),
                        result_date=datetime.date.today(),input_file=infile,output_file='')
        P.save()
        delete_old_results()
        my_form_data={'sifter_choices':'EXP-Model','ExpWeight_hidden':'0.7'
        ,'active_tab_hidden':'by_protein'}

        '''msg='results in: http://sifter.berkeley.edu/results-id=%s\n'%job_id
        msg+='Job submitted on: %s\n'%datetime.date.today()
        msg+='query_method: %s\n'%'by_protein'
        msg+='SIFTER choice: %s\n'%'EXP-Model'
        msg+='EXP Weight: %s\n'%0.7
        msg+='Number of proteins: %s\n'%1
        msg+='Species: %s\n'%0
        msg+='Number of functions: %s\n'%0
        msg+='Number of sequences: %s\n'%0
        send_mail('SIFTER-WEB run for Job ID:%s\n'%job_id, msg, 'sifter@compbio.berkeley.edu',['sahraeian.m@gmail.com'], fail_silently=False)'''
        run_sifter_job.delay(my_form_data,job_id)
        return HttpResponseRedirect('/results-id=%s'%job_id, {'results':''})        
    elif 's-taxid' in qdict:
        my_species=qdict['s-taxid'][0]
        form = InputForm()
        form.fields['active_tab_hidden'].widget.attrs['value'] = 'by_species'
        form.fields['sp_selected_hidden'].widget.attrs['value'] = my_species
        context={}
        context_class=RequestContext        
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
        context_class=RequestContext        
        context['form']=form
        context['response']='Hi'
        taxid=Taxid.objects.filter(tax_id=my_species).values('tax_name','tax_id')[0]
        context['spf_selected']='%s (%s)'%(taxid['tax_name'],taxid['tax_id'])
        return render(request, 'home.html', context)

def autocomplete(request):
    sqs=SearchQuerySet()
    dbs=request.GET.get('dbs', '')
    if dbs=='all':
        search_in=['term','taxid','unip']
    else:
        search_in=[dbs]
        
    suggestions=[]
    if 'term' in search_in:
        sqs1 = sqs.autocomplete(content_auto_name=request.GET.get('q', ''))[:5]
        sqs2 = sqs.autocomplete(content_auto_acc=request.GET.get('q', ''))[:5]    
        sqs5 = sqs.filter(text=request.GET.get('q', ''),django_ct='term_db.term')[:5]
        suggestions.extend([{'url':result.object.get_absolute_url(),'label':"%s (%s)"%(result.object.name,result.object.acc)} for result in sqs5+sqs1+sqs2])
    if 'taxid' in search_in:
        sqs3 = sqs.autocomplete(content_auto_taxname=request.GET.get('q', ''))[:5]
        sqs4 = sqs.autocomplete(content_auto_taxid=request.GET.get('q', ''))[:5]
        sqs6 = sqs.filter(text=request.GET.get('q', ''),django_ct='taxid_db.taxid')[:5]
        suggestions.extend([{'url':result.object.get_absolute_url(),'label':"%s (taxid:%s)"%(result.object.tax_name,result.object.tax_id)} for result in sqs6+sqs3+sqs4])
    if 'unip' in search_in:
        if len(request.GET.get('q', ''))>7:
            sqs7=list(set(SifterResultsReady.objects.filter(uniprot_id=request.GET.get('q', '')).values_list('uniprot_id',flat=True)))
            suggestions.extend([{'url':'/predictions/?protein=%s'%w,'label':w} for w in sqs7])
    # Make sure you return a JSON object, not a bare list.
    # Otherwise, you could be vulnerable to an XSS attack.
    the_data = json.dumps({
        'results': suggestions
    })
    return HttpResponse(the_data, content_type='application/json')