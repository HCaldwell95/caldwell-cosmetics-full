from django import template

register = template.Library()

@register.filter
def rc_area(card, n):       return getattr(card, f"area_{n}", "")
@register.filter
def rc_skin_type(card, n):  return getattr(card, f"skin_type_{n}", "")
@register.filter
def rc_spot(card, n):       return getattr(card, f"spot_size_{n}", "")
@register.filter
def rc_fluence(card, n):    return getattr(card, f"fluence_{n}", "")
@register.filter
def rc_pulses(card, n):     return getattr(card, f"pulses_{n}", "")
@register.filter
def rc_delay(card, n):      return getattr(card, f"delay_{n}", "")
@register.filter
def rc_shots(card, n):      return getattr(card, f"shots_{n}", "")
@register.filter
def rc_cost(card, n):       return getattr(card, f"cost_{n}", None)
@register.filter
def attr_row(card, n):      return bool(getattr(card, f"area_{n}", ""))

@register.filter
def attr_row(obj, n):
    """
    Example: checks if row n exists (custom logic needed)
    """
    return bool(getattr(obj, f"area_{n}", None))