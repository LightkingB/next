def to_bool(value):
    if str(value).lower() in ("no", "n", "false", "f", "0", "0.0", "", "none", "None", "[]", "{}"): return False
    return True
