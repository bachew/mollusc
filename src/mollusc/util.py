# -*- coding: utf-8 -*-
import six


def list_not_str(obj):
    if obj is None:
        return obj

    if hasattr(obj, '__iter__') and not isinstance(obj, six.string_types):
        return list(obj)

    return [obj]


def make_object_module(mod, obj):
    for key in dir(obj):
        if key.startswith('_'):
            continue

        value = getattr(obj, key)

        if callable(value):
            mod[key] = value
