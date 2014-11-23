from django.shortcuts import render,render_to_response,RequestContext
#from django.template import  Context
#from django.template.loader import get_template
from django import forms
from django.http import HttpResponseRedirect
from django.core.exceptions import ValidationError
from django.forms.util import ErrorList
from django.contrib import messages
from sifter_web.tasks import run_sifter_job
from results.models import SIFTER_Output
from taxid_db.models import Taxid
import datetime
import random
import pickle
from term_db.models import Term
import os
import operator

from chartit import DataPool, Chart
from scripts.estimate_time import estimate_time, get_processing_time
from estimatedb.models import Errorhistogrambars

INPUT_DIR=os.path.join(os.path.dirname(__file__),"input")

class InputForm(forms.Form):
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
        form = InputForm()

    return render(request, 'home.html', {'form': form,'response': 'Hi'})



def find_go_name_acc(ts):
    res0=Term.objects.filter(term_id__in=ts).values('term_id','name','acc')
    idx_to_go_name={}
    for w in res0:
        idx_to_go_name[w['term_id']]=[w['acc'],w['name']]
    return idx_to_go_name

def show_results(request,job_id):
    
    my_object=SIFTER_Output.objects.filter(job_id=job_id)
    if not len(my_object)==1:
        messages.success(request,'Error in the job_id. Number of hits=%s'%(len(my_object)))       
        return render(request, 'results.html', {'my_object':'','result':'','pending':False})
    my_object=my_object[0]
    print my_object.output_file
    if my_object.output_file=='':
        messages.success(request,'Thanks! You have successfully submitted your SIFTER query.')
        return render(request, 'results.html', {'my_object':my_object,'result':'','pending':False})        
    else:
        messages.success(request,'Your SIFTER query results are ready.')
        if not my_object.query_method=='by_sequence':
            res,taxids,unip_accs=pickle.load(open(my_object.output_file))
            terms=set([v for w in res.values() for v in w])                
            idx_to_go_name=find_go_name_acc(terms)
            result=[]
            for j,gene in enumerate(res):
                res_sorted=sorted(res[gene].iteritems(),key=operator.itemgetter(1),reverse=True)
                tax_obj=Taxid.objects.filter(tax_id=taxids[gene])
                if tax_obj:
                    tax_name=tax_obj[0].tax_name
                else:
                    tax_name=taxids[gene]
                result.append([gene,unip_accs[gene],tax_name,taxids[gene],'','','',3])
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
                    if i<end_i:                    
                        result.append(['','','','',idx_to_go_name[term][0],idx_to_go_name[term][1],str(score),0])
                    else:
                        result.append(['','','','',idx_to_go_name[term][0],idx_to_go_name[term][1],str(score),1])
                        break
                result.append(['','','','','','','',2])        
            print my_object.query_method
            if my_object.query_method == 'by_protein':
                data=pickle.load(open(my_object.input_file))
                my_genes=data['proteins']
                rest=set(my_genes)-set(res.keys())
                print len(set(my_genes))
                for j,gene in enumerate(rest):
                    result.append([gene,'?','?','','','','',3])
                    result.append(['','','','','','','',2])        
        
    
            return render(request, 'results.html', {'my_object':my_object,'result':result,'pending':False})
            
        else:
            res,taxids,unip_accs,blast_hits,connected=pickle.load(open(my_object.output_file))
            terms=set([v for w in res.values() for v in w])                
            idx_to_go_name=find_go_name_acc(terms)
            result=[]
            for query, hits in blast_hits.iteritems():
                result_q=[]
                for j,hit in enumerate(hits):
                    gene=hit[0]
                    print res.keys()
                    res_sorted=sorted(res[gene].iteritems(),key=operator.itemgetter(1),reverse=True)
                    tax_obj=Taxid.objects.filter(tax_id=taxids[gene])
                    if tax_obj:
                        tax_name=tax_obj[0].tax_name
                    else:
                        tax_name=taxids[gene]
                    result_q.append([gene,unip_accs[gene],tax_name,taxids[gene],hit[1],hit[2],hit[3],3])
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
                        if i<end_i:                    
                            result_q.append(['','','','',idx_to_go_name[term][0],idx_to_go_name[term][1],str(score),0])
                        else:
                            result_q.append(['','','','',idx_to_go_name[term][0],idx_to_go_name[term][1],str(score),1])
                            break
                    result_q.append(['','','','','','','',2])
                result.append([query,result_q])   
            return render(request, 'results.html', {'my_object':my_object,'result':result,'pending':False})
        
        

