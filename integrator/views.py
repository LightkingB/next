from django.shortcuts import render


def integrator_index(request):
    # if not request.user.is_authenticated:
    #     return redirect("integrator:next-teacher-login")
    context = {
        "navbar": "integrator"
    }
    return render(request, "teachers/integrator.html", context)
