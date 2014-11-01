from django.shortcuts import render,render_to_response,RequestContext
#from django.template import  Context
#from django.template.loader import get_template
from django import forms
from django.http import HttpResponseRedirect
from django.core.exceptions import ValidationError
from django.forms.util import ErrorList

class InputForm(forms.Form):
    input_queries = forms.CharField(widget=forms.Textarea(attrs={'rows':3, 'placeholder':'Enter query proteins','class':'form-control','id':'input_queries'}),label='Input Queries', max_length=100000,required=False)
    query_uploader = forms.FileField(widget=forms.FileInput(attrs={'id':'query_uploader'}),required=False)
    input_species = forms.CharField(widget=forms.TextInput(attrs={'placeholder':'Enter query species Taxonomy ID','class':'form-control','id':'input_species'}),label='Input Species', max_length=1000,required=False)
    input_function = forms.CharField(widget=forms.Textarea(attrs={'rows':3, 'placeholder':'Enter query functions','class':'form-control','id':'input_function'}),label='Input Function', max_length=100000,required=False)
    function_uploader = forms.FileField(widget=forms.FileInput(attrs={'id':'function_uploader'}),required=False)
    input_function_sp = forms.CharField(widget=forms.Textarea(attrs={'rows':2, 'placeholder':'Enter query functions','class':'form-control','id':'input_function_sp'}),label='Input Function Sp', max_length=100000,required=False)
    function_sp_uploader = forms.FileField(widget=forms.FileInput(attrs={'id':'function_sp_uploader'}),required=False)
    input_sequence = forms.CharField(widget=forms.Textarea(attrs={'rows':10, 'placeholder':'Enter query sequences','class':'form-control','id':'input_sequence'}),label='Input Sequences', max_length=100000,required=False)
    sequence_uploader = forms.FileField(widget=forms.FileInput(attrs={'id':'sequence_uploader'}),required=False)
    input_email = forms.CharField(widget=forms.EmailInput(attrs={'id':'input_email','placeholder':'Enter email','class':'form-control',}),label='Input Email', max_length=100,required=False)
    sifter_choices = forms.ChoiceField(widget=forms.RadioSelect, choices=(('EXP-Model', 'Only use experimental evidence (SIFTER EXP-Model)',)
        , ('ALL-Model', 'Use both experimental and non-experimental evidence (SIFTER ALL-Model)',)),initial='EXP-Model',required=False)
    active_tab_hidden = forms.CharField(widget=forms.HiddenInput(attrs={'id':'active_tab_hidden'}),initial='by_protein',required=False)
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

            return render(request, 'home.html', {'form': form, 'response':form.cleaned_data['ExpWeight_hidden']})
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
