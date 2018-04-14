# -*- coding: utf-8 -*-
from mollusc import sh2 as sh
import logging


class TestContext(object):
    def test_context_manager(self):
        orig_level = logging.getLogger().level
        assert sh.logger_level == orig_level

        with sh.context(logger_level=logging.DEBUG):
            assert sh.logger_level == logging.DEBUG

        assert sh.logger_level == orig_level

    def test_decorator(self):
        @sh.context(logger_level=logging.DEBUG)
        def func():
            assert sh.logger_level == logging.DEBUG\

        orig_level = logging.getLogger().level
        func()
        assert sh.logger_level == orig_level


def test_log():
    sh.log(logging.INFO, 'information')
    sh.log_error('error')
