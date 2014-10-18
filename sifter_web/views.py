from django.shortcuts import render,render_to_response,RequestContext
#from django.template import  Context
#from django.template.loader import get_template


def home(request):
    return render_to_response("home.html",
                              locals(),
                              context_instance=RequestContext(request))

