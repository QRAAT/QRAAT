from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class People(User):
	class Meta:
		db_table = "People"
		
	institution = models.CharField(max_length=40)
	start_date = models.DateField(auto_now=True)
	end_date = models.DateField()
