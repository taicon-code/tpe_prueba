from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Acceso a items de diccionarios en templates"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, 0)
    return 0

@register.filter(name='key')
def key_filter(dictionary, key):
    """Alias para get_item - acceso por clave en diccionarios"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, 0)
    return 0
