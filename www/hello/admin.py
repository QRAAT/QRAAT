#from hello.models import Poll, Choice
#from django.contrib import admin

#admin.site.register(Poll)

#class ChoiceInline(admin.TabularInline):
#  model = Choice
#  extra = 3

#class PollAdmin(admin.ModelAdmin):
#  fieldsets = [
#    (None,                {'fields': ['question']}),
#    ('Date information',  {'fields': ['pub_date'], 'classes': ['collapse']}),
#  ]
#  inlines = [ChoiceInline]
#  list_display = ('question', 'pub_date', 'was_published_today')

#admin.site.register(Poll, PollAdmin)
