from django import template

register = template.Library()


@register.filter
def join_names(data):
    if not data:
        return ""
    return " ".join(item.get("type", "") for item in data if "type" in item).strip()
