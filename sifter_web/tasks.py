from __future__ import absolute_import

from sifter_web.celery import app
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'sifter_web.settings'



from sifter_web.scripts.sqlite_query import find_results,find_results_domain

def aaa(x,y):
    return x-y

@app.task
def add(x, y):
    return aaa(x,y)
    
    #return x + y


@app.task
def mul(x, y):
    return x * y


@app.task
def xsum(numbers):
    return sum(numbers)


@app.task
def run_sifter_job(my_form_data,job_id):
    return find_results(my_form_data,job_id)
   
@app.task
def run_sifter_job_domain(q_gene,sifter_EXP_choices,ExpWeight_hidden):
    return find_results_domain(q_gene,sifter_EXP_choices,ExpWeight_hidden)
