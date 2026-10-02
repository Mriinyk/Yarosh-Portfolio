from urllib import request
from django.shortcuts import render


def index(request):
    return render(request, 'yarosh_website/index.html')
