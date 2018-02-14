def extract_keys(d, *keys):
    new = {}
    for key in keys:
        new[key] = d[key]
    return new


def maybe_extract_keys(d, keys):
    if not isinstance(keys, dict):
        keys = {key: None for key in keys}
    new = {}
    for key in keys:
        try:
            new[key] = d[key]
        except KeyError:
            new[key] = keys[key]
    return new
