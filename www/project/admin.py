"""This module contains Form objects for Django's admin pages"""

from django.contrib import admin
from models import Tx, TxMake, Deployment, Target
from models import Site, Location, Project
from models import AuthProjectCollaborator, AuthProjectViewer
from models import TxParameters, TxMakeParameters


class SiteAdmin(admin.ModelAdmin):
    list_display = (
        'ID', 'name', 'location',
        'latitude', 'longitude', 'easting',
        'northing', 'utm_zone_number', 'utm_zone_letter', 'elevation')


class LocationAdmin(admin.ModelAdmin):
    list_display = (
        'ID', 'name', 'location',
        'latitude', 'longitude', 'easting',
        'northing', 'utm_zone_number', 'utm_zone_letter',
        'elevation', 'is_hidden')

    list_filter = ('is_hidden',)

    ordering = ('-is_hidden', 'ID')


class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        'ID', 'ownerID', 'name',
        'description', 'is_public', 'is_hidden')

    list_filter = ('is_public', 'is_hidden')

    ordering = ('-is_hidden', 'ID')


class AuthProjectViewerAdmin(admin.ModelAdmin):
    list_display = (
        'ID', 'groupID', 'projectID', 'Project_name')

    def Project_name(self, obj):
        return obj.projectID.name


class AuthProjectCollaboratorAdmin(admin.ModelAdmin):
    list_display = (
        'ID', 'groupID', 'projectID', 'Project_name')

    def Project_name(self, obj):
        return obj.projectID.name


class TransmitterAdmin(admin.ModelAdmin):
    list_display = (
        'ID', 'name', 'serial_no', 'frequency', 'is_hidden',
        'Project_name', 'Model', 'Manufacturer')

    list_filter = ('is_hidden',)

    ordering = ('-is_hidden', 'ID')

    def Project_name(self, obj):
        return obj.projectID.name

    def Model(self, obj):
        return obj.tx_makeID.model

    def Manufacturer(self, obj):
        return obj.tx_makeID.manufacturer

    def save_model(self, request, obj, form, change):
        """
        Overrided method to add tx_parameters after inserting tx
        """
        super(TransmitterAdmin, self).save_model(request, obj, form, change)
        Tx = obj
        Tx_make_parameters = TxMakeParameters.objects.filter(
                tx_makeID=Tx.tx_makeID)
        
        # Add tx_parameters for each make_parameter
        for parameter in Tx_make_parameters:
            TxParameters.objects.create(
                txID=Tx,
                name=parameter.name,
                value=parameter.value)


class TransmitterInline(admin.StackedInline):
    model = Tx


class TxMakeAdmin(admin.ModelAdmin):
    list_display = ('ID', 'manufacturer', 'model', 'demod_type')
    ordering = ('ID',)
    list_filter = ('demod_type',)
    inlines = [TransmitterInline, ]


class TxParametersAdmin(admin.ModelAdmin):
    list_display = (
        'ID', 'name', 'value', 
        'txID', 'Tx_name', 'Project_name')

    ordering = ('ID',)

    def Tx_name(self, obj):
        return obj.txID.name

    def Project_name(self, obj):
        return obj.txID.projectID.name


class TxMakeParametersAdmin(admin.ModelAdmin):
    list_display = ('ID', 'name', 'value', 
                    'tx_makeID', 'Tx_model')
    ordering = ('ID',)

    def Tx_model(self, obj):
        return obj.tx_makeID.model


class DeploymentAdmin(admin.ModelAdmin):
    list_display = ('ID', 'name', 'time_start',
                    'time_end', 'txID', 'targetID', 'projectID',
                    'Project_name', 'is_active', 'is_hidden')

    list_filter = ('is_active', 'is_hidden')

    ordering = ('ID',)

    def Project_name(self, obj):
        return obj.projectID.name


class TargetAdmin(admin.ModelAdmin):
    list_display = ('ID', 'name', 'description', 
                    'max_speed_family', 'speed_burst', 'speed_sustained', 'speed_limit',
                    'projectID', 'Project_name', 'is_hidden')

    list_filter = ('is_hidden',)

    ordering = ('ID',)

    def Project_name(self, obj):
        return obj.projectID.name


admin.site.register(Target, TargetAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(Site, SiteAdmin)
admin.site.register(Tx, TransmitterAdmin)
admin.site.register(TxParameters, TxParametersAdmin)
admin.site.register(TxMake, TxMakeAdmin)
admin.site.register(TxMakeParameters, TxMakeParametersAdmin)
admin.site.register(Deployment, DeploymentAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(AuthProjectViewer, AuthProjectViewerAdmin)
admin.site.register(AuthProjectCollaborator, AuthProjectCollaboratorAdmin)
