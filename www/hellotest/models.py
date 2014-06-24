from django.db import models
from django.forms import ModelForm

from django.db import models
from django.forms import ModelForm

class Query(models.Model):
  name = models.CharField(max_length=255)
  url  = models.TextField()
  source = models.CharField(max_length=255)
  request = models.CharField(max_length=255)
                       
  def __unicode__(self):
    return u'%s %s %s' % (self.name, self.source, self.request)

class QueryForm(ModelForm):
  class Meta:
    model = Query
