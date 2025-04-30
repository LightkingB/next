from django import template

register = template.Library()


@register.filter
def join_names(data):
    if not data:
        return ""
    return " ".join(item.get("type", "") for item in data if "type" in item).strip()


@register.simple_tag
def get_stage_button_class(counter):
    """Возвращает словарь с классом кнопки и иконки в зависимости от этапа."""
    if counter == 1:
        return {'btn_class': 'btn-success', 'icon_class': 'fas fa-hourglass-half'}
    elif counter == 2:
        return {'btn_class': 'btn-warning', 'icon_class': 'fas fa-hourglass-half'}
    elif counter == 3:
        return {'btn_class': 'btn-danger', 'icon_class': 'fas fa-hourglass-half'}
    else:
        return {'btn_class': 'btn-secondary', 'icon_class': 'fas fa-dot-circle'}
