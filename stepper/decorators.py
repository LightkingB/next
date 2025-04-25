from bsadmin.services import UserService
from stepper.services import StepperService


def with_stepper(view_func):
    def wrapper(request, *args, **kwargs):
        request.stepper = StepperService()
        request.bs = UserService()
        return view_func(request, *args, **kwargs)

    return wrapper
