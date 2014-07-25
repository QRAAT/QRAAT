# qraat_ui/forms.py

from django import forms
from qraat_ui.models import Site, Deployment, Position
from django.shortcuts import render, redirect

# Select position or track data.
DATA_CHOICES = [
  ('1', 'Position'),
  ('2', 'Track'),
]

# Display data points as lines or as marker points.
DISPLAY_CHOICES = [
  ('1', 'Points'),
  ('2', 'Lines'),
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


# Choices for transmitter dropdown menu. Sorted by "Active", then number

def get_choices(deps=[]):
  #print "==========" + str(depID)
  choices_list = []
  for dep in deps:
    choices_list.append((dep.ID, dep.ID))
  return choices_list



#Fields for html form that queries and sets preferences
class Form(forms.Form):

  def __init__(self, deps=[], data=None):
    #self.deployment_id = depID
    super(forms.Form, self).__init__(data)
    self.fields['trans'].choices = get_choices(deps)
  
  #def clean_my_field(self):
  #  if len(self.clearned_data['trans']) > 3:
  #    raise forms.ValidationError('Select no more than 3.')
  #  return self.cleaned_data['trans']

  data_type = forms.ChoiceField(
            choices=DATA_CHOICES, 
            required=True, 
            label='Data Type', 
            initial='1'
            )

  trans = forms.MultipleChoiceField(
            choices = get_choices(),
            #widget = forms.SelectMultiple(),
            widget = forms.CheckboxSelectMultiple(),
            required = True,
            label = 'DeploymentID(s)',
            #initial = '63'
              #Note: initial doesn't work. it sets choices to '6' and '3'
              #To set initial value, in views.py:
                #instance_of_form.fields['trans'].initial = ['63']
            )

  #for integration with user authentication 
  #trans = TransChoiceField(
  #        label='Transmitter', 
  #        initial=63)
  
  display_type = forms.ChoiceField(
            choices=DISPLAY_CHOICES, 
            required=True, 
            label='Display Type', 
            initial="1")

  dt_fr = forms.DateTimeField(
            required = True, 
            label="From date/time (yyyy-mm-dd hh-mm-ss)",
            initial="2013-08-13 13:57:16")
  
  dt_to = forms.DateTimeField(
            required = True, 
            label="To date/time (yyyy-mm-dd hh-mm-ss)",
            initial="2014-06-16 21:28:12")
  
  lk_l = forms.FloatField(
            required=True, 
            label="Likelihood Lower Bound", 
            initial=0.0)
  
  lk_h = forms.FloatField(
            required=True, 
            label="Likelihood Upper Bound", 
            initial=2000.0)
  
  act_l = forms.FloatField(
            required=True, 
            label="Activity Lower Bound", 
            initial=0.0)
  
  act_h = forms.FloatField(
            required=True, 
            label="Activity Upper Bound", 
            initial=2.0)
  
  graph_data = forms.ChoiceField(
            choices=GRAPH_CHOICES, 
            required = True, 
            label='Graph Data Type', 
            initial="1")
  
  sites = forms.BooleanField(
            required=True, 
            label="Show Site Locations",
            initial=True)

      #  zoom = forms.ChoiceField(
      #   choices=ZOOM_CHOICES, 
      #   required = True, 
      #   label='Default Zoom', 
      #   initial=14)

      #  activity = forms.BooleanField(
      #   required=True, 
      #   label="Show Activity", 
      #   initial=False)

      #  ll = forms.BooleanField(
      #   required=True, 
      #   label="Show Lat, Lon", 
      #   initial=True)

      #  ne = forms.BooleanField(
      #   required = True, 
      #   label="Show Northing, Easting", 
      #   initial=True)

      #  lk = forms.BooleanField(
      #   required = True, 
      #   label="Show Likelihood", 
      #   initial=True)


