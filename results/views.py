from django.shortcuts import render
from models import SIFTER_Output
def latest_books(request):
    book_list = SIFTER_Output.objects.order_by('-submit_date')[:10]
    return render(request, 'latest_books.html', {'book_list': book_list})

# Create your views here.
