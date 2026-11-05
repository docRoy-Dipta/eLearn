from django import template

register = template.Library()


@register.filter
def get_item(dictionary, course_code):
    return dictionary.get(course_code)