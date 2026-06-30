def user_role_names(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return set()
    cached = getattr(request, "_user_role_names", None)
    if cached is None:
        cached = set(request.user.roles.values_list("name", flat=True))
        request._user_role_names = cached
    return cached
