# -*- coding: utf-8 -*-
from mollusc.dist import Twine


class TestTwine(object):
    def test_register_command(self):
        twine = Twine(username='registrar', password='reg1strar')
        assert twine.get_command('register', 'package.whl', {'-c': 'test register'}) == [
            'twine',
            'register',
            '--repository-url', Twine.DEFAULT_REPO_URL,
            '-u', 'registrar',
            '-c', 'test register',
            'package.whl'
        ]

    def test_upload_command(self):
        twine = Twine(username='uploader', password='upl0ader')
        assert twine.get_command('upload', ['package.whl', 'package.tar.gz'], {'-c': 'test upload'}) == [
            'twine',
            'upload',
            '--repository-url', Twine.DEFAULT_REPO_URL,
            '-u', 'uploader',
            '-c', 'test upload',
            'package.whl', 'package.tar.gz'
        ]
