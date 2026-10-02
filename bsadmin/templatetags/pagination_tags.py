from django import template

register = template.Library()


@register.simple_tag
def page_window(page_obj, on_each_side=2, on_ends=1):
    """Номера страниц с многоточиями: 1 … 4 5 [6] 7 8 … 20 (None — многоточие)."""
    paginator = page_obj.paginator
    return [
        None if number == paginator.ELLIPSIS else number
        for number in paginator.get_elided_page_range(page_obj.number, on_each_side=on_each_side, on_ends=on_ends)
    ]


@register.simple_tag(takes_context=True)
def page_url(context, number):
    """Ссылка на страницу с сохранением всех остальных GET-параметров (фильтры, поиск, сортировка)."""
    request = context.get("request")
    params = request.GET.copy() if request else None
    if params is None:
        return f"?page={number}"
    params["page"] = number
    return "?" + params.urlencode()
