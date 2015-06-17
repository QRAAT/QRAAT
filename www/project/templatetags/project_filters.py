"""This module contains template tags 

For more information about template tags see:
    https://docs.djangoproject.com/en/dev/howto/custom-template-tags/
"""

from django import template
register = template.Library()


@register.filter(name='is_owner')
def is_owner(project, user):
    """Check if a given user owns a given project"""

    return project.is_owner(user)


@register.filter(name='is_collaborator')
def is_collaborator(project, user):
    """Check if a given user is a given project collaborator"""

    return project.is_collaborator(user)


@register.filter(name="get_fields")
def get_fields(obj):
    """Return field values for a given model"""

    return [dict(name=field.name,
                 verbose_name=field.verbose_name,
                 string_value=field.value_to_string(obj))
            for field in obj._meta.fields]


@register.filter(name="get_attr")
def get_attr(obj, attr_name):
    """This function returns the value of a given attr"""

    return getattr(obj, attr_name)
