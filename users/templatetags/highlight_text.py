from django.utils.safestring import mark_safe
from django import template
from django.template.defaultfilters import stringfilter
register = template.Library()


@register.filter
@stringfilter
def highlight_text(text, search):
    words = search.split()
    for word in words:
        text = text.replace(
            word.lower(), '<span style="background-color: #FFFF00">{}</span>'.format(word.lower()))
        text = text.replace(
            word.capitalize(), '<span style="background-color: #FFFF00">{}</span>'.format(word.capitalize()))

    return mark_safe(text)
