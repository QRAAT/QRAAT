from django import template
register = template.Library()


@register.filter(name='is_owner')
def is_owner(project, user):
    return project.is_owner(user)

@register.filter(name='is_collaborator')
def is_collaborator(project, user):
    return project.is_collaborator(user)
