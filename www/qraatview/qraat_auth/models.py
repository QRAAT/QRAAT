from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import User

# Create your models here.


class QraatUserManager(BaseUserManager):
    """ User manager that creates and save a user at qraat User table """
    def create_user(self, email, first_name, last_name, password=None):
        if not email:
            raise ValueError("Users must have an email address")
        if not first_name:
            raise ValueError("Users must have a first name")
        if not last_name:
            raise ValueError("Users must have a last name")

        user = self.model(
            email=self.normalize_email(email),
            first_name=first_name, last_name=last_name)

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, password):
        user = self.create_user(
            email, first_name, last_name, password=password)
        user.is_admin = True

        user.save(using=self._db)
        return user


class QraatUser(AbstractBaseUser):
    class Meta:
        db_table = "User"

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=40)
    last_name = models.CharField(max_length=40)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = QraatUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ("first_name", "last_name")

    def get_full_name(self):
        return "%s %s" % (self.first_name, self.last_name)

    def get_short_name(self):
        return self.first_name

    def has_perm(self, perm, obj=None):
        return True  # TODO: Implement has_perm

    def has_module_perms(self, app_label):
        return True  # TODO: Implement has_module_perms

    @property
    def is_staff(self):
        return self.is_admin


class QraatUserBackend(object):
    """ User authentication backed.
            Authenticates user against the qraat user database"""
    def authenticate(self, username=None, password=None):
        try:
            q_user = QraatUser.objects.get(email=username)
        except QraatUser.DoesNotExist:
            return None
        else:
            if q_user.check_password(password):  # Matching user password
                try:  # If user doesn't exist creates it
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    user = User(username=username)

                    if q_user.is_admin:  # Set user permissions
                        user.is_staff = True
                        user.is_superuser = True

                    user.save()

                return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except:
            return None
