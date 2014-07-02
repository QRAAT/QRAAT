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

ZOOM_CHOICES = []
i = 1
while (i<=20):
  ZOOM_CHOICES.append([i, i])
  i+=1

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
  data_type = forms.ChoiceField(choices=DATA_CHOICES, required=True, label='Data Type', initial='pos')
  trans = forms.ChoiceField(choices=get_choices(), label='Transmitter', initial=63)
  dt_fr = forms.DateTimeField(required = True, 
          label="From date/time (yyyy-mm-dd hh-mm-ss)", 
          initial="2014-06-15 20:57:16")
          #default=datetime.now
  dt_to = forms.DateTimeField(required = True, 
          label="To date/time (yyyy-mm-dd hh-mm-ss", 
          initial="2014-06-16 10:01:10")
  zoom = forms.ChoiceField(choices=ZOOM_CHOICES, required = True, label='Default Zoom', initial=14)
  ll = forms.BooleanField(required=True, label="Show Lat, Lon", initial=True)
  ne = forms.BooleanField(required = True, label="Show Northing, Easting", initial=True)
  lk = forms.BooleanField(required = True, label="Show Likelihood", initial=True)
  lk_l = forms.FloatField(required=True, label="Likelihood Lower Bound", initial=500.0)
  lk_h = forms.FloatField(required=True, label="Likelihood Upper Bound", initial=1000.0)
  activity = forms.BooleanField(required=True, label="Show Activity", initial=True)
