from django import forms
from models import Project, TxMake
from models import Tx, Target, Deployment, Location
from models import TxMakeParameters, TxParameters
from django.contrib.auth.models import User
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
        if commit:
            project.ownerID = self.ownerID
            project.save()

        return project


class UserModelChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name()


class EditProjectForm(ProjectForm):

    def __init__(self, user=None, *args, **kwargs):
        super(EditProjectForm, self).__init__(user, *args, **kwargs)
        project = super(ProjectForm, self).save(commit=False)

        # Set values for selection
        viewers_selected_choices = [
            u.pk for u in project.get_viewers_group().user_set.all()]
        viewers_choices = User.objects.exclude(id=project.ownerID)
        # selected values
        self.fields["viewers"].initial = viewers_selected_choices
        self.fields["viewers"].queryset = viewers_choices  # all values

        collaborators_selected_choices = [
            u.pk for u in project.get_collaborators_group().user_set.all()]
        collaborators_choices = User.objects.exclude(id=project.ownerID)
        self.fields["collaborators"].initial = collaborators_selected_choices
        self.fields["collaborators"].queryset = collaborators_choices

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

        viewers_group = project.get_viewers_group()
        collaborators_group = project.get_collaborators_group()
        users = User.objects.all().exclude(id=project.ownerID)

        viewers = self.cleaned_data.get("viewers")
        collaborators = self.cleaned_data.get("collaborators")

        for user in users:
            if user in viewers:
                viewers_group.user_set.add(user)
            elif user not in viewers and user in viewers_group.user_set.all():
                viewers_group.user_set.remove(user)

            if user in collaborators:
                collaborators_group.user_set.add(user)
            elif user not in collaborators and\
                    user in collaborators_group.user_set.all():
                collaborators_group.user_set.remove(user)

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
