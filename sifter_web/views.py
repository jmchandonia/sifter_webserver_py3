from django.shortcuts import render,render_to_response,RequestContext
#from django.template import  Context
#from django.template.loader import get_template
from django import forms
from django.http import HttpResponseRedirect


def home(request):
    return render_to_response("home.html",
                              locals(),
                              context_instance=RequestContext(request))


class NameForm(forms.Form):
    your_name = forms.CharField(label='Your name', max_length=100)

def get_name(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = NameForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            return HttpResponseRedirect('/thanks/')

    # if a GET (or any other method) we'll create a blank form
    else:
        form = NameForm()

    return render(request, 'query.html', {'form': form})


class InputForm(forms.Form):
    input_queries = forms.CharField(widget=forms.Textarea(attrs={'rows':3, 'placeholder':'Enter query proteins','class':'form-control','id':'input_queries'}),label='Input Queries', max_length=100000)
    query_uploader = forms.FileField()
    input_species = forms.CharField(widget=forms.TextInput(attrs={'placeholder':'Enter query species Taxonomy ID','class':'form-control','id':'input_species'}),label='Input Species', max_length=1000)
    input_function = forms.CharField(widget=forms.Textarea(attrs={'rows':3, 'placeholder':'Enter query functions','class':'form-control','id':'input_function'}),label='Input Function', max_length=100000)
    function_uploader = forms.FileField()
    input_function_sp = forms.CharField(widget=forms.Textarea(attrs={'rows':2, 'placeholder':'Enter query functions','class':'form-control','id':'input_function_sp'}),label='Input Function Sp', max_length=100000)
    function_sp_uploader = forms.FileField()
    input_email = forms.CharField(widget=forms.EmailInput(attrs={'id':'input_email','placeholder':'Enter email','class':'form-control',}),label='Input Email', max_length=100)
    sifter_choices = forms.ChoiceField(widget=forms.RadioSelect, choices=(('EXP-Model', 'Only use experimental evidence (SIFTER EXP-Model)',)
        , ('ALL-Model', 'Use both experimental and non-experimental evidence (SIFTER ALL-Model)',)),initial='EXP-Model')
def get_input(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = InputForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            return HttpResponseRedirect('/thanks/')

    # if a GET (or any other method) we'll create a blank form
    else:
        form = InputForm()

    return render(request, 'home.html', {'form': form})
