#from hello.models import Position
from django.contrib import admin
from qraat_ui.models import sitelist, track, tx_ID, TxType, TxInfo
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
    list_display = ('ID', 'active', 'tx_info_ID')
    list_filter = ('active',)
    ordering = ('ID',)


class TxInfoAdmin(admin.ModelAdmin):
    list_display = ('ID', 'tx_type_ID', 'manufacturer', 'model')
    list_fiter = ('tx_type_ID', )
    ordering = ('ID',)


class TxTypeAdmin(admin.ModelAdmin):
    list_display = ('ID', 'RMG_type', 'tx_table_name')
    list_filter = ('RMG_type', )
    ordering = ('ID', )


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
