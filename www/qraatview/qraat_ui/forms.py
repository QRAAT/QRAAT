# qraat_ui/forms.py

from django import forms
from qraat_ui.models import Site, Deployment, Position
from django.shortcuts import render, redirect

# Select Position vs. Track data
DATA_CHOICES = [
  ('0', 'Select data type...'),
  ('1', 'Position'),
  ('2', 'Track'),
]

DISPLAY_CHOICES = [
  ('0', 'Select display type...'),
  ('1', 'Lines'),
  ('2', 'Points'),
]
  # Select default zoom. Currently disabled because it's annoying when
  # re-updating flot and google maps in response to html form re-submit.
#ZOOM_CHOICES = []
#i = 1
#while (i<=20):
#  ZOOM_CHOICES.append([i, i])
#  i+=1

# Select whether the graph shows Likelihood or Activity data.
GRAPH_CHOICES = [
('1', 'Likelihood'),
('2', 'Activity')
]

# Choices for the dropdown menu for transmitters. Sorted by "Active"
def get_choices():
  choices_list = []
  choices_list.append((0, "Select transmitter..."))
  for d in Deployment.objects.order_by('-is_active', 'ID'):
    if (d.is_active == 0):
      d.is_active = "inactive"
    elif (d.is_active == 1):
      d.is_active = "ACTIVE"
    choices_list.append((d.ID, str(d.ID)+' - '+d.is_active))
  return choices_list

# the fields for the html form for setting preferences
class Form(forms.Form):
  data_type = forms.ChoiceField(choices=DATA_CHOICES, required=True, label='Data Type', initial='1')
  trans = forms.ChoiceField(choices=get_choices(), label='Transmitter', initial=63)
  display_type = forms.ChoiceField(choices=DISPLAY_CHOICES, required=True, label='Display Type', initial="2")
  dt_fr = forms.DateTimeField(required = True, 
          label="From date/time (yyyy-mm-dd hh-mm-ss)",
          initial="2013-08-13 13:57:16")
  dt_to = forms.DateTimeField(required = True, 
          label="To date/time (yyyy-mm-dd hh-mm-ss)",
          initial="2014-06-16 21:28:12")
  lk_l = forms.FloatField(required=True, label="Likelihood Lower Bound", initial=200.0)
  lk_h = forms.FloatField(required=True, label="Likelihood Upper Bound", initial=1000.0)
  act_l = forms.FloatField(required=True, label="Activity Lower Bound", initial=0.0)
  act_h = forms.FloatField(required=True, label="Activity Upper Bound", initial=1.3)
  graph_data = forms.ChoiceField(choices=GRAPH_CHOICES, required = True, label='Graph Data Type', initial="1")
  sites = forms.BooleanField(required=True, label="Show Site Locations", initial=True)
#  zoom = forms.ChoiceField(choices=ZOOM_CHOICES, required = True, label='Default Zoom', initial=14)

#  activity = forms.BooleanField(required=True, label="Show Activity", initial=False)
#  ll = forms.BooleanField(required=True, label="Show Lat, Lon", initial=True)
#  ne = forms.BooleanField(required = True, label="Show Northing, Easting", initial=True)
#  lk = forms.BooleanField(required = True, label="Show Likelihood", initial=True)
