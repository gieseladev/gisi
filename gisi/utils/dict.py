from collections import Iterable, Mapping, MutableMapping


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


class _NullObject:
    def __repr__(self):
        return "undefined"

    def __getitem__(self, item):
        return self

    def __getattr__(self, item):
        return self

    def __bool__(self):
        return False


NullObject = _NullObject()


class JsonList(list):
    def __iter__(self):
        return iter([self[i] for i in range(len(self))])

    def __getitem__(self, item):
        obj = super().__getitem__(item)
        if isinstance(obj, Mapping):
            return JsonObject(obj)
        elif isinstance(obj, list):
            return JsonList(obj)
        else:
            return obj


class JsonObject(dict):
    def __getitem__(self, item):
        obj = super().__getitem__(item)
        if isinstance(obj, Mapping):
            return JsonObject(obj)
        elif isinstance(obj, list):
            return JsonList(obj)
        else:
            return obj

    def __getattr__(self, item):
        return self.__getitem__(item)


class MultiDict(MutableMapping):
    def __init__(self, *items):
        self._items = []
        self._length = 0

        for keys, value in items:
            keys = list(keys) if isinstance(keys, Iterable) else [keys]
            for key in keys:
                if key in self:
                    raise KeyError(f"\"{key}\" duplicate key!")
            self._items.append((keys, value))
            self._length += 1

    def __repr__(self):
        return f"<Multidict {self.items}>"

    def __getitem__(self, item):
        try:
            value = next(value for keys, value in self._items if item in keys)
        except StopIteration:
            raise KeyError
        else:
            return value

    def __setitem__(self, key, value):
        for index, (keys, value) in enumerate(self._items):
            if key in keys:
                self._items[index][1] = value
                break
        else:
            self._items.append(([key], value))
            self._length += 1

    def __delitem__(self, key):
        for index, (keys, value) in enumerate(self._items):
            if key in keys:
                break
        else:
            raise KeyError
        del self._items[index]
        self._length -= 1

    def __iter__(self):
        for keys, value in self._items:
            yield keys

    def __len__(self):
        return self._length

    def add_key(self, key, new_key):
        if new_key in self:
            raise KeyError(f"\"{new_key}\" already exists!")
        for index, (keys, value) in enumerate(self._items):
            if key in keys:
                self._items[index][0].append(new_key)
                break
        else:
            raise KeyError
