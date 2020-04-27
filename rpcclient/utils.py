import json

def to_str(obj, encoding='utf-8'):
    if isinstance(obj, bytes):
        return obj.decode(encoding)
    elif isinstance(obj, (dict, list, tuple)):
        return json.dumps(obj)
    return str(obj)

def to_bytes(obj, encoding='utf-8'):
    if isinstance(obj, bytes):
        return obj
    else:
        obj = to_str(obj, encoding)
    return obj.encode(encoding)