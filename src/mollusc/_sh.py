# -*- coding: utf-8 -*-
import errno
import glob
import os
import sys
import shutil
import six
import stat
import subprocess
import tempfile
from contextlib import contextmanager
from mollusc import util
from os import path as osp
from pprint import pformat
from subprocess import list2cmdline


class Shell(object):
    DEFAULT_ENCODING = 'utf-8'

    class CommandFailed(Exception):
        def __init__(self, msg, orig_error):
            super(Shell.CommandFailed, self).__init__(msg)
            self.orig_error = orig_error

    class CommandNotFound(Exception):
        pass

    def __init__(self, stdout=sys.stdout, stderr=sys.stderr):
        self.stdout = stdout
        self.stderr = stderr

        def get_enc(f):
            return getattr(f, 'encoding', None)

        self.encoding = get_enc(stdout) or get_enc(stderr) or self.DEFAULT_ENCODING

    def echo(self, msg, error=False, end='\n', flush=True):
        s = self.format_message(msg)
        file = self.stderr if error else self.stdout
        six.print_(s, file=file, end=end, flush=flush)

    def format_message(self, msg):
        if isinstance(msg, six.text_type):
            return msg

        if isinstance(msg, six.binary_type):
            return msg.decode(self.encoding)

        return pformat(msg)

    def ensure_dir(self, path):
        self.echo('Ensure dir {!r}'.format(path))

        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST or not osp.isdir(path):
                raise

        return path

    @contextmanager
    def temp_dir(self, **kwargs):
        path = tempfile.mkdtemp(**kwargs)
        try:
            yield path
        finally:
            shutil.rmtree(path)

    @property
    def working_dir(self):
        return os.getcwd()

    def change_dir(self, path):
        self.echo('cd {!r}'.format(path))
        unchanger = UnchangeDir(self, self.working_dir, path)
        os.chdir(path)
        return unchanger

    @contextmanager
    def change_temp_dir(self, **kwargs):
        with self.temp_dir(**kwargs) as path, self.change_dir(path):
            yield path

    def call(self, cmd, check=True, **kwargs):
        self._update_call_kwargs(kwargs)
        cmdline = self._cmdline_echo(cmd, check, kwargs)
        self.echo(cmdline)
        func = subprocess.check_call if check else subprocess.call
        return self._call(func, cmd, **kwargs)

    def output(self, cmd, check=True, **kwargs):
        self._update_call_kwargs(kwargs)
        cmdline = self._cmdline_echo(cmd, check, kwargs)
        self.echo('$({})'.format(cmdline))

        try:
            output = self._call(subprocess.check_output, cmd, **kwargs)
        except self.CommandFailed as e:
            if check:
                raise
            else:
                output = e.orig_error.output

        return output.decode(self.encoding)

    def _update_call_kwargs(self, kwargs):
        stderr_to_stdout = kwargs.pop('stderr_to_stdout', False)

        if stderr_to_stdout:
            kwargs['stderr'] = subprocess.STDOUT

    def _cmdline_echo(self, cmd, check, kwargs):
        cmdline = list2cmdline(cmd)

        if kwargs.get('stderr') == subprocess.STDOUT:
            cmdline = '{} >&2'.format(cmdline)

        if not check:
            cmdline = '({}) || true'.format(cmdline)

        return cmdline

    def _call(self, func, cmd, **kwargs):
        try:
            return func(cmd, **kwargs)
        except subprocess.CalledProcessError as e:
                cmdline = list2cmdline(cmd)
                msg = 'Command {!r} failed with error code {!r}'.format(cmdline, e.returncode)
                raise self.CommandFailed(msg, e)
        except EnvironmentError as e:
            if e.errno == errno.ENOENT:
                cmdline = list2cmdline(cmd)
                msg = 'Command {!r} not found, did you install it?'.format(cmdline)
                six.raise_from(self.CommandNotFound(msg), e)
            else:
                raise

    def write(self, path, data, echo=True):
        if echo:
            self.echo('Writing {!r}'.format(self.relpath(path)))

        # TODO: atomic write
        with open(path, 'w') as f:
            f.write(data)

    def chmod_x(self, path, echo=True):
        if echo:
            self.echo('chmod +x {!r}'.format(self.relpath(path)))

        mode = os.stat(path).st_mode
        os.chmod(path, mode | stat.S_IXGRP | stat.S_IXUSR | stat.S_IXOTH)

    def path(self, *names):
        return osp.join(*names)

    def abspath(self, *names):
        return osp.abspath(self.path(*names))

    def relpath(self, *names):
        return osp.relpath(self.path(*names))

    def remove(self, paths, echo=True):
        if paths is None:
            return

        def rm(path):
            if echo:
                self.echo('Removing {!r}'.format(self.relpath(path)))

            try:
                try:
                    shutil.rmtree(path)
                except OSError as e:
                    if e.errno == errno.ENOTDIR:
                        pass  # continue remove the file
                    else:
                        raise

                os.remove(path)
            except OSError as e:
                if e.errno == errno.ENOENT:
                    pass  # OK if not exists
                else:
                    raise

        for path in util.list_not_str(paths):
            rm(path)

    def glob(self, path):
        return list(glob.glob(path))

    # TODO: basename, split_path, merge_path, split_ext, merge_ext
    # TODO: is_file, is_dir, is_exec, is_readable, is_writable, etc
    # TODO: test, validate
    # TODO: list_dir, glob
    # TODO: copy, rename


class UnchangeDir(object):
    def __init__(self, sh, orig_dir, from_dir):
        self.sh = sh
        self.orig_dir = orig_dir
        self.from_dir = from_dir

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.sh.echo('cd {!r}  # back from {!r}'.format(self.orig_dir, self.from_dir))
        os.chdir(self.orig_dir)


sh = Shell()
