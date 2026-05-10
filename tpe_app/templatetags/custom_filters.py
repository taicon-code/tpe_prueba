from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Obtiene un elemento de un diccionario por clave dinámica"""
    if dictionary is None:
        return None
    if isinstance(key, tuple):
        # Si la clave es una tupla, usarla directamente (para acceso a tuplas como claves)
        return dictionary.get(key)
    # Si es un string, devolver el valor o un dict vacío para calendario
    return dictionary.get(key, {'agendas': [], 'feriado': None})
