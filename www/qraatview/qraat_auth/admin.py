from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from qraat_auth.forms import UserForm, QraatUserChangeForm

# Register your models here.

from qraat_auth.models import QraatUser

class QraatUserAdmin(UserAdmin):
	form = QraatUserChangeForm 
	add_form = UserForm
	
	list_display = ("username", "email", "is_active", "is_admin")
	list_filter= ("is_admin",)
	filter_horizontal = ()

	fieldsets = (
		(None, {'fields': ('username','email',"password")}),
		("Permissions", {'fields': ('is_active', 'is_admin')})
		)
	add_fieldsets = (
		(None, {'classes': ('wide',),
			'fields': ('username', 'password1', 'password2', 'email') }),
		)	

admin.site.register(QraatUser, QraatUserAdmin)
