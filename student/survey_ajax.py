from django.http import JsonResponse
from django.template.loader import render_to_string


def is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def ajax_modal(form_html):
    return JsonResponse({"html_form": form_html})


def ajax_success(message, **extra):
    return JsonResponse({"form_is_valid": True, "message": message, **extra})


def ajax_error(message, form_html):
    return JsonResponse(
        {"form_is_valid": False, "message": message, "html_form": form_html},
        status=400,
    )


def render_modal(request, template, context):
    return render_to_string(template, context, request=request)
