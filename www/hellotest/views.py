# Create your views here.
from django import forms
from django.http import HttpResponse
from django.shortcuts import render
from django.template import RequestContext, loader
from django.views.generic.edit import FormView

from hellotest.models import QueryForm

def index(request, **kwargs):
  form = QueryForm()
  return render(request,'/index.html', {'form': form})
