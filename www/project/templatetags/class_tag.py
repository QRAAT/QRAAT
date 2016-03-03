"""This module contains template tags 

For more information about template tags see:
    https://docs.djangoproject.com/en/dev/howto/custom-template-tags/
"""
from django import template
register = template.Library()


@register.filter(name='get_class')
def get_class(value):
    """This function returns the class name of a given object
    It is used by the templates to now what is the instance type of objects"""
    return value.__class__.__name__
