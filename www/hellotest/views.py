# hellotest views.py

from django.http import HttpResponse
from django.shortcuts import render
from django.template import RequestContext, loader
from django.views.generic.edit import FormView

from hellotest.models import QueryForm
from hellotest.forms import Form2, Form3

def index(request, **kwargs):
  form = QueryForm()
  form2 = Form2()
  form3 = Form3()

  context = {
            'form': form,
            'form2': form2,
            'form3': form3,
            }
  return render(request,'hellotest/index.html', context)
