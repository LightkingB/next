from bsadmin.consts import USER_ROLES


def roles_constants(request):
    if request.user.is_authenticated:
        roles = set(request.user.roles.values_list("name", flat=True))
    else:
        roles = set()

    return {"CUSTOM_ROLES": USER_ROLES, "DB_ROLES": roles}
