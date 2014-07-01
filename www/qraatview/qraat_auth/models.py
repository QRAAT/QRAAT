from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class People(models.Model):
	class Meta:
		db_table = "People"
		
	user = models.OneToOneField(User)
	email = models.EmailField(max_length=75, unique=True)
	first_name = models.CharField(max_length=40)
	last_name = models.CharField(max_length=70)
	institution = models.CharField(max_length=40)
	stat_date = models.DateField(auto_now=True)
	end_date = models.DateField()
