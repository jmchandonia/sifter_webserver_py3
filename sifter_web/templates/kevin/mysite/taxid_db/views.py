import itertools
from django.shortcuts import render
from ajax_search.forms import SearchForm

# Create your views here.
#def ():
#    return render_to_response('search.html', {'searchform': SearchForm()})

def search_helper(count, query):
    model_list = Taxid.objects.filter(tax_name__icontains=query, status=1)
    for L in range(1, count + 1):
        for subset in itertools.permutations(words, L):
            count1 = 1
            query1 = subset[0]
            while count1 != len(subset):
                query1 = query1 + " " + subset[count1]
                count1 += 1
            model_list = entry_list | Taxid.objects.filter(tax_name__icontains=query, status=1)
    return (model_list.distinct())
