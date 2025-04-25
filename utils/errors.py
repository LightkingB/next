from django.contrib import messages
from django.shortcuts import render


def handle_error(request, context, template_name, message=None):
    messages.error(request, message)
    return render(request, template_name, context)
