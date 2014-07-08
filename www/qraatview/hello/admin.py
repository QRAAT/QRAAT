#from hello.models import Position
from django.contrib import admin
from hello.models import sitelist, track, tx_ID, TxType, TxInfo
from hello.models import TxAlias, TxPulse
"""
#admin.site.register(Poll)

class ChoiceInline(admin.TabularInline):
  model = Choice
  extra = 3

class PollAdmin(admin.ModelAdmin):
  fieldsets = [
    (None,                {'fields': ['question']}),
    ('Date information',  {'fields': ['pub_date'], 'classes': ['collapse']}),
  ]
  inlines = [ChoiceInline]
  list_display = ('question', 'pub_date', 'was_published_today')
"""


class TransmitterAdmin(admin.ModelAdmin):
    list_display = ('ID', 'Manufacturer',
                    'Model', 'RMG_type', 'Tx_table_name', 'active')
    list_filter = ('active',)
    ordering = ('-active', 'ID')

    def Manufacturer(self, obj):
        return obj.tx_info_ID.manufacturer

    def Model(self, obj):
        return obj.tx_info_ID.model

    def RMG_type(self, obj):
        return obj.tx_info_ID.tx_type_ID.RMG_type

    def Tx_table_name(self, obj):
        return obj.tx_info_ID.tx_type_ID.tx_table_name


class TransmitterInline(admin.StackedInline):
    model = tx_ID


class TxInfoAdmin(admin.ModelAdmin):
    list_display = ('ID', 'tx_type_ID', 'manufacturer', 'model')
    list_fiter = ('tx_type_ID', )
    ordering = ('ID',)
    inlines = [TransmitterInline, ]


class TxTypeAdmin(admin.ModelAdmin):
    list_display = ('ID', 'RMG_type', 'tx_table_name')
    list_filter = ('RMG_type', )
    ordering = ('ID', )


class TxAliasAdmin(admin.ModelAdmin):
    list_display = ('ID', 'alias', 'tx_ID')


class TxPulseAdmin(admin.ModelAdmin):
    list_display = ('tx_ID', 'frequency', 'pulse_width',
            'pulse_rate', 'band3', 'band10')


class SiteListAdmin(admin.ModelAdmin):
    list_display = ('ID', 'name', 'location',
                    'latitude', 'longitude', 'easting', 'northing',
                    'utm_zone_number', 'utm_zone_letter',
                    'elevation', 'rx')
    ordering = ('ID',)


class TrackAdmin(admin.ModelAdmin):
    list_display = ('ID', 'depID', 'max_speed_family',
                    'speed_burst', 'speed_sustained', 'speed_limit')
    list_filter = ('max_speed_family', )
    ordering = ('ID', 'depID')


admin.site.register(sitelist, SiteListAdmin)
admin.site.register(track, TrackAdmin)
admin.site.register(tx_ID, TransmitterAdmin)
admin.site.register(TxInfo, TxInfoAdmin)
admin.site.register(TxType, TxTypeAdmin)
admin.site.register(TxAlias, TxAliasAdmin)
admin.site.register(TxPulse, TxPulseAdmin)
