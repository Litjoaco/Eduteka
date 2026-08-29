from django import template

register = template.Library()

@register.filter(name='dict_get')
def dict_get(d, key):
    if isinstance(d, dict):
        return d.get(key)
    return None

@register.filter(name='get_item')
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter(name='formato_pesos')
def formato_pesos(val):
    if val is None or val == '':
        return "$0"
    try:
        val_int = int(round(float(val)))
        if val_int < 0:
            formatted = f"{abs(val_int):,}".replace(",", ".")
            return f"-${formatted}"
        formatted = f"{val_int:,}".replace(",", ".")
        return f"${formatted}"
    except (ValueError, TypeError):
        return f"${val}"

@register.filter(name='formato_numero')
def formato_numero(val):
    if val is None or val == '':
        return "0"
    try:
        val_int = int(round(float(val)))
        if val_int < 0:
            formatted = f"{abs(val_int):,}".replace(",", ".")
            return f"-{formatted}"
        return f"{val_int:,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(val)

@register.filter(name='formato_pesos_signo')
def formato_pesos_signo(val):
    if val is None or val == '':
        return "$0"
    try:
        val_int = int(round(float(val)))
        if val_int > 0:
            formatted = f"{val_int:,}".replace(",", ".")
            return f"+${formatted}"
        elif val_int < 0:
            formatted = f"{abs(val_int):,}".replace(",", ".")
            return f"-${formatted}"
        return "$0"
    except (ValueError, TypeError):
        return f"${val}"
