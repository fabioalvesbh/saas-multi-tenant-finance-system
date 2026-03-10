# /tenant_management/templatetags/visitas_extras.py

from django import template

register = template.Library()

@register.filter
def dict_get(d, key):
    if not isinstance(d, dict):
        return 0
    return d.get(key, 0)

