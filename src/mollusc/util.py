# -*- coding: utf-8 -*-
import six


def list_not_str(obj):
    if obj is None:
        return obj

    if hasattr(obj, '__iter__') and not isinstance(obj, six.string_types):
        return list(obj)

    return [obj]
