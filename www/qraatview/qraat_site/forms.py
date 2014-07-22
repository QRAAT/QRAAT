from django import forms
from qraat_site.models import Project, AuthProjectViewer, Tx
from qraat_site.models import AuthProjectCollaborator, TxMake
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


class AddTransmitterForm(forms.ModelForm):
    class Meta:
        model = Tx
        exclude = ["projectID", "is_hidden"]

    def __init__(self, project=None, *args, **kwargs):
        self.project = project
        super(AddTransmitterForm, self).__init__(*args, **kwargs)
        self.fields['tx_makeID'].choices = [ (t_make.ID, t_make) for t_make in TxMake.objects.all()]

    name = forms.CharField(
        label="Transmitter name",
        widget=forms.TextInput(
            attrs={"class": "form-control",
                   "max_length": 50}))

    serial_no = forms.CharField(
        label="Serial number",
        widget=forms.TextInput(
            attrs={"class": "form-control",
                   "max_length": 50}))

    tx_makeID = forms.ChoiceField(
        label="Manufacturer",
        choices = [],
        widget=forms.Select(
            attrs={"class": "form-control"}))

    frequency = forms.FloatField(
        label = "Frequency",
        widget=forms.NumberInput(
            attrs={"class": "form-control"}))

    def clean_tx_makeID(self):
        makeid_form_data = self.cleaned_data.get("tx_makeID")
        return TxMake.objects.get(ID=makeid_form_data)

    def save(self, commit=True):
        Tx = super(AddTransmitterForm, self).save(commit=False)
        Tx.projectID=self.project

        if commit == True:
            Tx.save()

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
        gviewers_name =  "%d_viewers" % project.ID
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


# class AccountChangeForm(forms.ModelForm):
#     class Meta:
#         model = QraatUser
#         fields = ("first_name", "last_name")


# class PasswordChangeForm(forms.ModelForm):
#     cur_password = forms.CharField(
#         label='Current password', widget=forms.PasswordInput)

#     password1 = forms.CharField(
#         label='New password', widget=forms.PasswordInput)

#     password2 = forms.CharField(
#         label='Password confirmation', widget=forms.PasswordInput)

#     class Meta:
#         model = QraatUser
#         fields = ()

#     def clean_cur_password(self):
#         cur_password = self.cleaned_data.get("cur_password")
#         user = super(PasswordChangeForm, self).save(commit=False)
#         if cur_password and not user.check_password(cur_password):
#             raise forms.ValidationError("Current password don't match")

#         return cur_password

#     def clean_password2(self):
#         password1 = self.cleaned_data.get("password1")
#         password2 = self.cleaned_data.get("password2")

#         if password1 and password2 and password1 != password2:
#             raise forms.ValidationError("Passwords don't match")

#         return password2

#     def save(self, commit=True):
#         user = super(PasswordChangeForm, self).save(commit=False)
#         user.set_password(self.cleaned_data["password1"])
#         if commit:
#             user.save()
#         return user
