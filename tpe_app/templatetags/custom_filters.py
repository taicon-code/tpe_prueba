from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Obtiene un elemento de un diccionario por clave dinámica"""
    if dictionary is None:
        return None
    return dictionary.get(key, {'agendas': [], 'feriado': None})
