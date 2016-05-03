from datetime import datetime, timedelta
from django import forms
from django.db import connection
from django.forms import widgets
from django.utils.safestring import mark_safe
from project.models import Site, Deployment
import utils


def get_processing_options():
    processing_options = [("estserver", "Server est"), ("server", "Server det"), ("site", "Site det")]
    return processing_options

class SubmitButton(forms.Widget):
    # only way that I found to add a button in the middle of a django form
    # buttons are usually added to the end of the form
    def __init__(self, name, value, label, attrs):
        self.name, self.value, self.label = name, value, label
        self.attrs = attrs
        
    def __unicode__(self):
        final_attrs = self.build_attrs(
            self.attrs,
            type="submit",
            name=self.name,
            value=self.value,
            )
        return mark_safe(u'<button%s>%s</button>' % (
            forms.widgets.flatatt(final_attrs),
            self.label,
            ))

class SubmitButtons(forms.Select):
    def __init__(self, attrs={}, choices=()):
        self.attrs = attrs
        self.choices = choices
        
    def render(self, name, value, attrs=None, choices=()):
        return mark_safe(u'<br/>%s' % u'\n'.join(
            [u'%s' % SubmitButton(name, value, label, self.attrs.copy()) for value, label in self.choices]
            ))

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

    move_interval = forms.ChoiceField(
              widget = SubmitButtons,
              choices = [('back', 'Back'), ('forward', 'Forward')]
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

class DashboardForm(forms.Form):
    def __init__(self, data = None):
        super(forms.Form, self).__init__(data)
        self.fields['info_sites'].choices = [('telemetry', 'telemetry'), ('detcount', 'detcount'), ('estcount', 'estcount'), ('timecheck', 'timecheck')]
        self.fields['info_deployments'].choices = [('est', 'est'), ('bearing', 'bearing'), ('position', 'position'), ('track_pos', 'track_pos')]
        self.fields['info_system'].choices = [('processing_statistics', 'processing_stats'), ('processing_cursor', 'processing_cursor')]
        
    datetime_start = forms.DateTimeField(
        required = True, 
        label="Start Date & Time (Pacific)",
        #[YYYY-MM-DD HH:MM:SS]
        widget = forms.TextInput(attrs={
          'class': 'filter',
          'size': '17'}),
        initial = (utils.get_local_now() - timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M:%S") # Displays current time in PST, minus 20 minutes
        )

    interval = forms.IntegerField(
        required = False,
        label = "Interval (minutes)",
        widget = forms.TextInput(attrs={
        'class': 'filter',
        'size': '10'}),
        initial = 10
        )

    info_sites = forms.MultipleChoiceField(
        widget = forms.CheckboxSelectMultiple(),
        required = True,
        label = 'Info|Site',
        initial = ['telemetry', 'detcount', 'estcount', 'timecheck']
        )

    info_deployments = forms.MultipleChoiceField(
        widget = forms.CheckboxSelectMultiple(),
        required = True,
        label = 'Info|Deployment',
        initial = ['est', 'bearing', 'position', 'track_pos']
        )

    info_system = forms.MultipleChoiceField(
        widget = forms.CheckboxSelectMultiple(),
        required = True,
        label = 'Info|System',
        initial = ['processing_statistics', 'processing_cursor']
        )

