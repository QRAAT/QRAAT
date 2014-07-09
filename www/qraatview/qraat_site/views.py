from django.shortcuts import render
from django.http import HttpResponse 

# Create your views here.

def index(request):
    nav_options = [{"url":"qraat/test1", "name":"Test1"},
                {"url": "qraat/test2", "name": "Test2"}]
    return render(
            request, "qraat_site/index.html",
            {'nav_options' : nav_options})
