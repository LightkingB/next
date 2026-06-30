from functools import wraps

from django.shortcuts import render

from bsadmin.role_utils import user_role_names
from student.consts import STSURVE


def survey_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if STSURVE not in user_role_names(request):
            return render(request, "students/survey_admin/denied.html", status=403)
        request.session["access"] = "survey"
        return view_func(request, *args, **kwargs)

    return wrapper
