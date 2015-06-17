from django import forms
from django.db import connection
from django.forms import widgets
from models import Site, Deployment
from datetime import datetime, timedelta


def get_processing_options():
    processing_options = [("estserver", "Server est"), ("server", "Server det"), ("site", "Site det")]
    return processing_options


class TimeSeriesGraphForm(forms.Form):
    def __init__(self, data = None):
        super(forms.Form, self).__init__(data)

    def get_site_choices(self):

        site_choices = []
        site_choices.append(('all', 'All Sites'))

        for site in Site.objects.all():
            site_choices.append( (str(site.name), (str(site.name)).capitalize()) )

        return site_choices

    def get_deployment_choices(self):
        """ Creates a list of tuples of all the deployments currently in the deployment table """
        deployment_choices = []

        for deployment in Deployment.objects.all():
            deployment_choices.append( (str(deployment.ID), (str(deployment.ID))) )

        return deployment_choices

    def get_graph_variables(self, table_name):
        """ Retrieves column names from the table_name table to display as graph options"""

        cursor = connection.cursor()
        query = "SELECT * FROM qraat." + table_name + " LIMIT 1"
        cursor.execute(query) # query to get a list of column names

        graph_variables = []
        if table_name == "telemetry":
            graph_variables.append(('all', 'All Graph Variables'))

        for graph_variable in cursor.description:
            graph_variables.append( (graph_variable[0], graph_variable[0]) )
          
        # remove some options - i.e. timestamp ???
        
        return graph_variables

    datetime_start = forms.DateTimeField(
              required = True, 
              label="Start Date & Time",
              #[YYYY-MM-DD HH:MM:SS]
              widget = forms.TextInput(attrs={
                'class': 'filter',
                'size': '17'}),
              initial = (datetime.now() - timedelta(hours=30)).strftime("%Y-%m-%d %H:%M:%S") # current datetime - 6 hours
              )
  
    datetime_end = forms.DateTimeField(
              required = True, 
              label="End Date & Time", 
              widget = forms.TextInput(attrs={
                'class': 'filter',
                'size': '17'}),
              initial = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # current datetime
              )

    start_timestamp = forms.FloatField(
              required = False,
              label = "Start Timestamp (UNIX)",
              widget = forms.TextInput(attrs={
              'class': 'filter',
              'size': '10'})
              )

    end_timestamp = forms.FloatField(
              required = False,
              label = "End Timestamp (UNIX)",
              widget = forms.TextInput(attrs={
              'class': 'filter',
              'size': '10'})
              )

    interval = forms.IntegerField(
              required = False,
              label = "Interval (in seconds)",
              widget = forms.TextInput(attrs={
              'class': 'filter',
              'size': '10'}),
              )

    graph_variables = forms.MultipleChoiceField(
              choices = [],
              widget = forms.CheckboxSelectMultiple(),
              required = True,
              label = 'Graph Variables',
              initial = ['all']
              )


class TelemetryGraphForm(TimeSeriesGraphForm):
    def __init__(self, data = None):
        super(TimeSeriesGraphForm, self).__init__(data = data)
        self.fields['graph_variables'].choices = self.get_graph_variables("telemetry")
        self.fields['site_names'].choices = self.get_site_choices()

    site_names = forms.MultipleChoiceField(
              widget = forms.CheckboxSelectMultiple(),
              required = True,
              label = 'Site Names',
              initial = ['all']
              )


class EstGraphForm(TimeSeriesGraphForm):
    def __init__(self, data = None):
        super(TimeSeriesGraphForm, self).__init__(data = data)
        self.fields['graph_variables'].choices = self.get_graph_variables("est")
        self.fields['site_names'].choices = self.get_site_choices()
        self.fields['deployment_id'].choices = self.get_deployment_choices()

    site_names = forms.MultipleChoiceField(
              widget = forms.CheckboxSelectMultiple(),
              required = True,
              label = 'Site Names',
              initial = ['all']
              )

    deployment_id = forms.MultipleChoiceField(
              required = True,
              label = 'Deployment ID',
              )


class ProcessingGraphForm(TimeSeriesGraphForm):
    def __init__(self, data = None):
        super(TimeSeriesGraphForm, self).__init__(data = data)
        self.fields['graph_variables'].choices = get_processing_options()
        self.fields['site_names'].choices = self.get_site_choices()

    site_names = forms.MultipleChoiceField(
              widget = forms.CheckboxSelectMultiple(),
              required = True,
              label = 'Site Names',
              initial = ['all']
              )

