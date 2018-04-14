# -*- coding: utf-8 -*-
from functools import wraps
import logging
import six


class Shell(object):
    def __init__(self):
        self.logger = logging.getLogger()

    def context(self, **attrs):
        return ShellContext(self, attrs)

    @property
    def logger_level(self):
        return self.logger.level

    @logger_level.setter
    def logger_level(self, level):
        self.logger.setLevel(level)

    def log(self, *args, **kwargs):
        self.logger.log(*args, **kwargs)

    def log_debug(self, *args, **kwargs):
        self.logger.debug(*args, **kwargs)

    def log_info(self, *args, **kwargs):
        self.logger.info(*args, **kwargs)

    def log_warning(self, *args, **kwargs):
        self.logger.warning(*args, **kwargs)

    def log_error(self, *args, **kwargs):
        self.logger.error(*args, **kwargs)

    def log_critical(self, *args, **kwargs):
        self.logger.critical(*args, **kwargs)

    def log_exception(self, *args, **kwargs):
        self.logger.exception(*args, **kwargs)


class ShellContext(object):
    def __init__(self, sh, attrs):
        self.sh = sh
        self.attrs = attrs
        self.orig_attrs = dict([(k, getattr(sh, k)) for k in attrs])

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return wrapper

    def __enter__(self):
        for key, value in six.iteritems(self.attrs):
            setattr(self.sh, key, value)

    def __exit__(self, exc_type, exc, tb):
        for key, value in six.iteritems(self.orig_attrs):
            setattr(self.sh, key, value)
