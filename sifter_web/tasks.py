from __future__ import absolute_import

from sifter_web.celery import app
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'sifter_web.settings'



from sifter_web.scripts.sqlite_query import find_results

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
   