# -*- coding: utf-8 -*-
import getpass
import os
import sys
from mollusc import sh, util


class NoCredentials(Exception):
    pass


class Twine(object):
    DEFAULT_REPO_URL = 'https://upload.pypi.org/legacy/'

    def __init__(self, username=None, password=None, repo_url=None):
        self.username = username
        self.password = password
        self.repo_url = repo_url

    def register(self, package, options={}):
        self.call('register', package, options)

    def upload(self, dist_files, options={}):
        self.call('upload', dist_files, options)

    def call(self, subcmd, args=[], options={}):
        cmd = self.get_command(subcmd, args, options)

        if not self.password and not self.password_in_keyring:
            target = '{!r} in {!r}'.format(self.username, self.repo_url)
            msg = 'Could not get password for {} from keyring'.format(target)

            if sys.stdin.isatty():
                sh.echo(msg)

                while not self.password:
                    self.password = getpass.getpass('Enter password for {}: '.format(target))
            else:
                raise NoCredentials(msg)

        env = os.environ.copy()

        if self.password:
            env['TWINE_PASSWORD'] = self.password

        sh.call(cmd, env=env)

    def get_command(self, subcmd, args, options):
        if not self.repo_url:
            self.repo_url = self.DEFAULT_REPO_URL

        if not self.username:
            self.username = getpass.getuser()

        cmd = [
            'twine', subcmd,
            '--repository-url', self.repo_url,
            '-u', self.username
        ]

        for name, value in options.items():
            cmd.append(name)
            cmd.append(value)

        cmd.extend(util.list_not_str(args))
        return cmd

    @property
    def password_in_keyring(self):
        if not hasattr(self, '_password_in_keyring'):
            self._password_in_keyring = False

            try:
                import keyring
            except ImportError:
                sh.echo('Keyring is not installed', error=True)
            else:
                try:
                    self._password_in_keyring = bool(keyring.get_password(self.repo_url, self.username))
                except RuntimeError as e:
                    sh.echo('keyring: {}'.format(e), error=True)

        return self._password_in_keyring
