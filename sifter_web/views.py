from django.shortcuts import render,render_to_response,RequestContext
#from django.template import  Context
#from django.template.loader import get_template
from django import forms
from django.http import HttpResponseRedirect
from django.core.exceptions import ValidationError
from django.forms.util import ErrorList

class InputForm(forms.Form):
    input_queries = forms.CharField(widget=forms.Textarea(attrs={'rows':3, 'placeholder':'Enter query proteins','class':'form-control','id':'input_queries'}),label='Input Queries', max_length=100000,required=False)
    query_uploader = forms.FileField(required=False)
    input_species = forms.CharField(widget=forms.TextInput(attrs={'placeholder':'Enter query species Taxonomy ID','class':'form-control','id':'input_species'}),label='Input Species', max_length=1000,required=False)
    input_function = forms.CharField(widget=forms.Textarea(attrs={'rows':3, 'placeholder':'Enter query functions','class':'form-control','id':'input_function'}),label='Input Function', max_length=100000,required=False)
    function_uploader = forms.FileField(required=False)
    input_function_sp = forms.CharField(widget=forms.Textarea(attrs={'rows':2, 'placeholder':'Enter query functions','class':'form-control','id':'input_function_sp'}),label='Input Function Sp', max_length=100000,required=False)
    function_sp_uploader = forms.FileField(required=False)
    input_email = forms.CharField(widget=forms.EmailInput(attrs={'id':'input_email','placeholder':'Enter email','class':'form-control',}),label='Input Email', max_length=100,required=False)
    sifter_choices = forms.ChoiceField(widget=forms.RadioSelect, choices=(('EXP-Model', 'Only use experimental evidence (SIFTER EXP-Model)',)
        , ('ALL-Model', 'Use both experimental and non-experimental evidence (SIFTER ALL-Model)',)),initial='EXP-Model',required=False)
    active_tab_hidden = forms.CharField(widget=forms.HiddenInput(attrs={'id':'active_tab_hidden'}),initial='by_protein',required=False)

    
    def check(cleaned_data,my_field,msg):
        my_field_data = cleaned_data.get(my_field)
        if not my_field_data:
            msg = 'The query proteins are not entered.'
            self._errors[my_field] = ErrorList([msg])
            del self.cleaned_data[my_field]
    
    def clean(self):
        active_tab=form.cleaned_data['active_tab_hidden']
        cleaned_data = super(InputForm, self).clean()
        if active_tab=='by_protein':
            check(cleaned_data,'input_queries','The query proteins are not entered.')


        #if self.cleaned_data['input_queries']!='1':
        #    msg = 'The type and organisssszation do not match.'
        #    self._errors['input_queries'] = ErrorList([msg])
        #    del self.cleaned_data['input_queries']
                
        return self.cleaned_data

    def set_active(self, active_tab):
        data = self.data.copy()
        data['active_tab_hidden'] = active_tab
        self.data = data

def get_input(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = InputForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            active_tab=form.cleaned_data['active_tab_hidden']
            form.set_active(active_tab)
            return render(request, 'home.html', {'form': form, 'response':active_tab })
            

    # if a GET (or any other method) we'll create a blank form
    else:
        form = InputForm()

    return render(request, 'home.html', {'form': form,'response': 'Hi'})
