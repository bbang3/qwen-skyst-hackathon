def patch(backups, target, attr, new_value):
    key = (target, attr)
    if key not in backups:
        backups[key] = getattr(target, attr)
    setattr(target, attr, new_value)
