from django import forms
from qraat_site.models import Project, AuthProjectViewer
from qraat_site.models import Tx, Target, Deployment, Location
from qraat_site.models import AuthProjectCollaborator, TxMake
from qraat_site.models import TxMakeParameters, TxParameters
from django.contrib.auth.models import User, Group
from django.contrib.admin.widgets import FilteredSelectMultiple


class ProjectForm(forms.ModelForm):

    def __init__(self, user=None, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        if user:
            self.ownerID = user.id

    class Meta:
        model = Project
        fields = ("name", "description", "is_public")

    name = forms.CharField(
        label="Project Name",
        widget=forms.TextInput(attrs={'class': 'form-control',
                                      'max_length': 50}))

    description = forms.CharField(
        label="Project Description",
        widget=forms.Textarea(attrs={'class': 'form-control',
                                     'rows': 10, 'cols': 40}))
    is_public = forms.BooleanField(
        label="Public project",
        required=False)

    def save(self, commit=True):
        project = super(ProjectForm, self).save(commit=False)
        project.ownerID = self.ownerID
        if commit:
            project.save()

        return project


class AddManufacturerForm(forms.ModelForm):
    class Meta:
        model = TxMake
        labels = {"demod_type": ("Demodulation type")}


class ProjectElementForm(forms.ModelForm):
    def __init__(self, project=None, *args, **kwargs):
        self.project = project
        super(ProjectElementForm, self).__init__(*args, **kwargs)

    def set_project(self, project):
        self.project = project

    def save(self, commit=True):
        proj_obj = super(ProjectElementForm, self).save(commit=False)
        proj_obj.projectID = self.project

        if commit:
            proj_obj.save()

        return proj_obj


class AddLocationForm(ProjectElementForm):
    class Meta:
        model = Location
        exclude = ["projectID", "is_hidden"]


class AddTargetForm(ProjectElementForm):
    class Meta:
        model = Target
        exclude = ["projectID", "is_hidden"]


class AddDeploymentForm(ProjectElementForm):
    class Meta:
        model = Deployment
        exclude = ["projectID", "is_hidden", "time_end"]

    txID = forms.ChoiceField()
    targetID = forms.ChoiceField()

    def set_project(self, project):
        self.project = project
        
        # constraint project's transmitters 
        self.fields["txID"].choices = [
            (tx.ID, tx) for tx in project.get_transmitters()]
        
        # constraint project's targets
        self.fields["targetID"].choices = [
            (target.ID, target) for target in project.get_targets()]

    def clean_txID(self):
        return Tx.objects.get(ID=self.cleaned_data.get("txID"))

    def clean_targetID(self):
        return Target.objects.get(ID=self.cleaned_data.get("targetID"))


class AddTransmitterForm(ProjectElementForm):
    class Meta:
        model = Tx
        exclude = ["projectID", "is_hidden"]
        labels = {"name": ("Transmitter name"),
                  "serial_no": ("Serial number"),
                  "tx_makeID": ("Manufacturer"),
                  "frequency": ("Frequency")}

    def save(self, commit=True):
        Tx = super(AddTransmitterForm, self).save(commit=False)
        Tx.projectID = self.project

        if commit is True:
            Tx.save()
            Tx_make_parameters = TxMakeParameters.objects.filter(
                tx_makeID=Tx.tx_makeID)

            for parameter in Tx_make_parameters:
                TxParameters.objects.create(
                    txID=Tx,
                    name=parameter.name,
                    value=parameter.value,
                    units=parameter.units)

        return Tx


class UserModelChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name()


class EditProjectForm(ProjectForm):
    # class Media:
    #     css = {
    #             'all':['admin/css/widgets.css',
    #                    'admin/css/uid-manage-form.css'],
    #             }
    #     js = ['/jsi18n/', '/static/admin/js/jquery.js',
    #           '/static/admin/js/core.js',
    #           '/static/admin/js/SelectBox.js']

    viewers = UserModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name="users", is_stacked=False))

    collaborators = UserModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name="users", is_stacked=False))

    def save(self, commit=True):
        project = super(ProjectForm, self).save(commit=False)
        gviewers_name = "%d_viewers" % project.ID
        gcollaborators_name = "%d_collaborators" % project.ID

        viewer_group = Group.objects.get(
            name=gviewers_name)

        collaborator_group = Group.objects.get(
            name=gcollaborators_name)

        for viewer in self.cleaned_data.get("viewers"):
            viewer_group.user_set.add(viewer)

        for collaborator in self.cleaned_data.get("collaborators"):
            collaborator_group.user_set.add(collaborator)

        if commit:
            project.save()
        return project
