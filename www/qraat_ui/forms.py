# qraat_ui/forms.py

from django import forms
from qraat_ui.models import Site, Deployment, Position
from django.shortcuts import render, redirect

# Select position or track data.
DATA_CHOICES = [('1', 'Position')]
#DATA_CHOICES = [('1', 'Position'), ('2', 'Track')]

# Display data points as lines or as marker points.
DISPLAY_CHOICES = [('1', 'Points')]
#DISPLAY_CHOICES = [('1', 'Points'), ('2', 'Lines')]

# Select whether the graph shows Likelihood or Activity data.
GRAPH_CHOICES = [('1', 'Likelihood'), ('2', 'Activity')]

# Choices for transmitter dropdown menu. Sorted by "Active", then number
def get_choices(deps=[]):
  choices_list = []
  for dep in deps:
    choices_list.append((dep.ID, dep.ID))
  return choices_list

def get_deps(req_deps=[]):
  deps_list = []
  for d in req_deps:
    #limits req_deps list to 4 deps
    if len(deps_list) < 4:
      deps_list.append((d.ID, d.ID))
  return deps_list
  
#Fields for html form that queries and sets preferences
class Form(forms.Form):
  def __init__(self, deps=[], req_deps=[], data=None):
    #self.deployment_id = depID
    super(forms.Form, self).__init__(data)
    self.fields['deployment'].choices = get_choices(deps)
    #self.fields['graph_dep'].choices = get_deps(req_deps)
    #Use get_choices(req_deps) if don't need to limit num of selected deps

  #def clean_my_field(self):
  #  if len(self.clearned_data['deployment']) > 3:
  #    raise forms.ValidationError('Select no more than 3.')
  #  return self.cleaned_data['deployment']
  
  deployment = forms.MultipleChoiceField(
            #choices = get_choices(),
            #widget = forms.SelectMultiple(), #hold down CTRL to select all
            widget = forms.CheckboxSelectMultiple(),
            required = True,
            label = 'Deployment IDs (displays first 4)')
            #Note: initial doesn't work. it sets choices to '6' and '3'
            #In views.py: instance_of_form.fields['deployment'].initial = ['63']
 
  data_type = forms.ChoiceField(
            choices=DATA_CHOICES, 
            required=True, 
            label='Data Product', 
            initial='1')
 
  display_type = forms.ChoiceField(
            choices=DISPLAY_CHOICES, 
            required=True, 
            label='Display on Map as', 
            initial="1")

  sites = forms.BooleanField(
            required=True, 
            label="View Site Locations",
            initial=True)



  #Filtering parameters

  datetime_from = forms.DateTimeField(
            required = True, 
            label="Start Date & Time",
            #[YYYY-MM-DD HH:MM:SS]
            widget = forms.TextInput(attrs={
              'class': 'filter',
              'size': '17'}),
            initial="2014-08-01 12:00:00")
  
  datetime_to = forms.DateTimeField(
            required = True, 
            label="End Date & Time", 
            widget = forms.TextInput(attrs={
              'class': 'filter',
              'size': '17'}),
            initial="2014-08-01 17:00:00")
  
  likelihood_low = forms.FloatField(
            required=True, 
            label="Likelihood Lowest", 
            widget = forms.TextInput(attrs={
              'class': 'filter',
              'size': '5'}),
            initial=15.0)
  
  likelihood_high = forms.FloatField(
            required=True,
            label="Highest", 
            widget = forms.TextInput(attrs={
              'class': 'filter',
              'size': '5'}),
            initial=2000.0)
  
  activity_low = forms.FloatField(
            required=True, 
            label="Activity Lowest", 
            widget = forms.TextInput(attrs={
              'class': 'filter',
              'size': '5'}),
            initial=0.0)
  
  activity_high = forms.FloatField(
            required=True, 
            label="Highest", 
            widget = forms.TextInput(attrs={
              'class': 'filter',
              'size': '5'}),
            initial=2.0)

  #graph data

  #graph_dep = forms.ChoiceField(
  #          required = True,
  #          label='Deployment displayed')
  #  #dynamic choices based on form-checked deployments

  graph_data = forms.ChoiceField(
            choices=GRAPH_CHOICES, 
            required = True, 
            label='Data displayed', 
            initial="1")


