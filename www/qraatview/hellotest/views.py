# hellotest views.py

from django.http import HttpResponse
from django.shortcuts import render
from django.template import RequestContext, loader
from django.views.generic.edit import FormView

from hellotest.models import QueryForm
from hellotest.forms import Form

def index(request, **kwargs):
  form = Form()
  context = {
            'form': form,
            }
  return render(request,'hellotest/index.html', context)
