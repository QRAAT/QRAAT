#from hello.models import Position
from django.contrib import admin
from hello.models import sitelist, track, tx_ID
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
admin.site.register(sitelist)
admin.site.register(track)
