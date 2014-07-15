from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from qraat_auth.forms import UserForm, QraatUserChangeForm

# Register your models here.

from qraat_auth.models import QraatUser


class QraatUserAdmin(UserAdmin):
    form = QraatUserChangeForm
    add_form = UserForm

    list_display = ("email", "first_name", "last_name", "is_active", "is_admin")
    list_filter = ("is_admin",)
    filter_horizontal = ()
    search_fields = ('email',)
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'first_name', 'last_name', 'password')}),
        ("Permissions", {'fields': ('is_active', 'is_admin')})
        )
    add_fieldsets = (
        (None, {'classes': ('wide',),
                'fields': ('email', 'first_name',
                           'last_name' 'password1', 'password2')}),
        )

admin.site.register(QraatUser, QraatUserAdmin)
