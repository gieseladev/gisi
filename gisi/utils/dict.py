def extract_keys(d, *keys):
    new = {}
    for key in keys:
        new[key] = d[key]
    return new