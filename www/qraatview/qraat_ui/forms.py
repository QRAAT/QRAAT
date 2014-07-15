# qraat_ui/forms.py

from django import forms
from qraat_ui.models import sitelist, tx_ID, Position, track
from django.shortcuts import render, redirect

DATA_CHOICES = [
  ('0', 'Select data type...'),
  ('1', 'Position'),
  ('2', 'Track'),
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

GRAPH_CHOICES = [
('1', 'Likelihood'),
('2', 'Activity')
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
  data_type = forms.ChoiceField(choices=DATA_CHOICES, required=True, label='Data Type', initial='1')
  trans = forms.ChoiceField(choices=get_choices(), label='Transmitter', initial=63)
  dt_fr = forms.DateTimeField(required = True, 
          label="From date/time (yyyy-mm-dd hh-mm-ss)",
          initial="2013-08-13 13:57:16")
  dt_to = forms.DateTimeField(required = True, 
          label="To date/time (yyyy-mm-dd hh-mm-ss)",
          initial="2014-06-16 21:28:12")
  lk_l = forms.FloatField(required=True, label="Likelihood Lower Bound", initial=200.0)
  lk_h = forms.FloatField(required=True, label="Likelihood Upper Bound", initial=1000.0)
  graph_data = forms.ChoiceField(choices=GRAPH_CHOICES, required = True, label='Graph Data Type', initial="1")
  sites = forms.BooleanField(required=True, label="Show Site Locations", initial=True)
#  zoom = forms.ChoiceField(choices=ZOOM_CHOICES, required = True, label='Default Zoom', initial=14)

#  activity = forms.BooleanField(required=True, label="Show Activity", initial=False)
#  ll = forms.BooleanField(required=True, label="Show Lat, Lon", initial=True)
#  ne = forms.BooleanField(required = True, label="Show Northing, Easting", initial=True)
#  lk = forms.BooleanField(required = True, label="Show Likelihood", initial=True)
