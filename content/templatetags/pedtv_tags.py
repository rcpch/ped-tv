from django import template

register = template.Library()


@register.filter
def format_duration(seconds):
    """Format a number of seconds as m:ss or h:mm:ss."""
    if seconds is None:
        return "\u2014"
    seconds = int(round(float(seconds)))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
