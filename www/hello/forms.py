from django import forms
from django.forms import ModelForm, Textarea
from hello.models import LatLng, Convert, Prefs

class PrefsForm(ModelForm):
  class Meta:
    model = Prefs
    fields = ('db', 'dtfr', 'tifr', 'tito')



#class DbForm(forms.Form):
#  db_selected = forms.CharField(_'db_selected), required=True)

#class PrefsForm(forms.ModelForm)
#  db = models.CharField(max_length=8, choice=DB_CHOICES)
#  dtfr = models.DateField(blank=True, null=True)
#  tifr = models.TimeField(blank=True, null=True)
#  dtto = models.DateField(blank=True, null=True)
#  tito = models.TimeField(blank=True, null=True)

#  class Meta:
#    model = Prefs

