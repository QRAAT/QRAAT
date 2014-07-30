from django import template
register = template.Library()


@register.filter(name='is_owner')
def is_owner(project, user):
    return project.is_owner(user)


@register.filter(name='is_collaborator')
def is_collaborator(project, user):
    return project.is_collaborator(user)


@register.filter(name="get_fields")
def get_fields(obj):
    return [dict(verbose_name=field.verbose_name,
            value=field.value_to_string(obj))
            for field in obj._meta.fields]
