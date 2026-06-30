from bsadmin.consts import USER_ROLES
from bsadmin.role_utils import user_role_names


def roles_constants(request):
    roles = user_role_names(request) if request.user.is_authenticated else set()
    return {"CUSTOM_ROLES": USER_ROLES, "DB_ROLES": roles}
