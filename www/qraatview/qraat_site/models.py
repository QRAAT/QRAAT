from django.db import models
from qraat_auth.models import QraatUser

# Create your models here.

class People(models.Model):
	class Meta:
		db_table = "People"
	user = models.OneToOneField(QraatUser)
	institution = models.CharField(max_length=40)
	start_date = models.DateField(auto_now=True)
	end_date = models.DateField()
