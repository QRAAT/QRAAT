from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import User, check_password

# Create your models here.

class QraatUserManager(BaseUserManager):
	def create_user(self, username, email, password=None):
		if not email:
			raise ValueError("Users must have an email address")
		
		user = self.model(username=username, email=self.normalize_email(email))

		user.set_password(password)
		user.save(using=self._db)
		return user	
		
	def create_superuser(self, username, email, password):
		user = self.create_user(username, email, password=password)
		user.is_admin = True

		user.save(using=self._db)
		return user

class QraatUser(AbstractBaseUser):
	class Meta:
		db_table = "User"
	
	username = models.CharField(max_length=40, unique=True)
	email = models.EmailField()
	is_admin = models.BooleanField(default=False)
	is_active = models.BooleanField(default=True)
	
	objects = QraatUserManager()
	
	USERNAME_FIELD = "username"
	REQUIRED_FIELDS = ("email",)

	def get_full_name(self):
		return self.username

	def get_short_name(self):
		return self.username

	def has_perm(self, perm, obj=None):
		return True

	def has_module_perms(self, app_label):
		return True

	@property
	def is_staff(self):
		return self.is_admin


class QraatUserBackend(object):
	def authenticate(self, username=None, password=None):
		try:
			q_user = QraatUser.objects.get(username=username)
		except QraatUser.DoesNotExist:
			return None
		else:
			if q_user.check_password(password):
				try:
					user = User.objects.get(username=username)
				except User.DoesNotExist:
					user = User(username=username)
					user.set_password(password)
					user.save()
				return user
		return None	
	

	def get_user(self, user_id):
		try:
			return User.objects.get(pk=user_id)
		except:
			return None
