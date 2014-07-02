# hellotest forms.py

from django import forms
from hello.models import sitelist, tx_ID, Position, track
from django.shortcuts import render, redirect

DATA_CHOICES = [
  ('0', 'Select data type...'),
  ('pos', 'Position'),
  ('trc', 'Track'),
]

PREF_CHOICES = [
  ('l_l', 'lat, lon'),
  ('lhd', 'likelihood'),
  ('act', 'activity')
]

def get_choices():
  choices_list = []
  choices_list.append((0, "Select transmitter..."))
  for t in tx_ID.objects.order_by('-active', 'ID'):
    if (t.active == 0):
      t.active = "inactive"
    elif (t.active == 1):
      t.active = "ACTIVE"
    choices_list.append((t.ID, str(t.ID)+' - '+t.active))
  return choices_list


class Form(forms.Form):
  data_type = forms.ChoiceField(choices=DATA_CHOICES, required=True, label='')
  transmitter = forms.ChoiceField(choices=get_choices(), label='')
  dt_fr = forms.DateTimeField(required = True, 
          label="From date/time", 
          initial="2014-06-10 10:01:10")
  dt_to = forms.DateTimeField(required = True, 
          label="To date/time", 
          initial="2014-06-10 10:01:10")
  lat_lon = forms.BooleanField(required=True, label="Lat, Lon")
  north_east = forms.BooleanField(required=True, label="Northing, Easting")
  likelihood = forms.BooleanField(required=True)
  activity = forms.BooleanField(required=True)

def show_form(request):
  form = Form(request.GET or None)
  return render(request, "index.html", {'form': form})

