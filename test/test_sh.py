# -*- coding: utf-8 -*-\
import os
import pytest
import subprocess
from mollusc import sh
from os import path as osp
from pprint import pformat
from six import StringIO
from textwrap import dedent


class Shell2(sh.Shell):
    def __init__(self):
        super(Shell2, self).__init__(StringIO(), StringIO())

    @property
    def stdout_str(self):
        return self.stdout.getvalue()

    @property
    def stderr_str(self):
        return self.stderr.getvalue()

    @property
    def stdout_first_line(self):
        return self.stdout_str.splitlines()[0]


@pytest.fixture
def sh2():
    return Shell2()


@pytest.fixture
def in_tmpdir(tmpdir):
    with tmpdir.as_cwd():
        yield tmpdir


class TestEcho(object):
    def test_real(self):
        sh.echo('Message')
        sh.echo('Message', error=True)

    def test_stdout_stderr(self, sh2):
        sh2.echo('Message')
        assert sh2.stdout_str == 'Message\n'
        assert sh2.stderr_str == ''
        sh2.echo('Error', error=True)
        assert sh2.stdout_str == 'Message\n'
        assert sh2.stderr_str == 'Error\n'

    def test_byte_string(self, sh2):
        sh2.echo(u'人'.encode('utf8'))
        assert sh2.stdout_str == u'人\n'

    def test_line_end(self, sh2):
        sh2.echo('Downloading...', end='')
        assert sh2.stdout_str == 'Downloading...'
        sh2.echo(' done')
        assert sh2.stdout_str == 'Downloading... done\n'

    def test_pprint(self, sh2):
        obj = {
            'abcd': [
                'a' * 10,
                'b' * 20,
                'c' * 30,
                'd' * 40
            ]
        }
        sh2.echo(obj, end='')
        assert sh2.stdout_str == pformat(obj)


class TestEnsureDir(object):
    def test_ensure(self, tmpdir):
        path = tmpdir.join('dir/subdir').strpath
        assert not osp.exists(path)
        ret_path = sh.ensure_dir(path)
        assert ret_path == path
        assert osp.isdir(path)

    def test_dir_exists(self, tmpdir):
        path = tmpdir.join('dir').strpath
        os.mkdir(path)
        sh.ensure_dir(path)

    def test_file_exists(self, tmpdir):
        tmpdir.join('file').write('')

        with pytest.raises(OSError):
            sh.ensure_dir(tmpdir.join('file').strpath)


def test_temp_dir(in_tmpdir):
    with sh.temp_dir() as path:
        assert osp.isdir(path)

    assert not osp.exists(path)


class TestChangeDir(object):
    def test_call(self, tmpdir):
        orig_dir = os.getcwd()
        assert osp.samefile(sh.working_dir(), orig_dir)
        sh.change_dir(tmpdir.strpath)

        try:
            assert osp.samefile(tmpdir.strpath, os.getcwd())
            assert osp.samefile(tmpdir.strpath, sh.working_dir())
        finally:
            os.chdir(orig_dir)

    def test_context(self, tmpdir):
        with sh.change_dir(tmpdir.strpath):
            assert osp.samefile(tmpdir.strpath, os.getcwd())

    def test_output(self, sh2, tmpdir):
        orig_dir = os.getcwd()

        with sh2.change_dir(tmpdir.strpath):
            pass

        assert sh2.stdout_str == dedent('''\
            cd {!r}
            cd {!r}  # back from {!r}
            ''').format(tmpdir.strpath, orig_dir, tmpdir.strpath)


def test_change_temp_dir(tmpdir):
    with sh.change_temp_dir() as path:
        assert osp.samefile(path, os.getcwd())

    assert not osp.exists(path)


class TestCall(object):
    def test_touch(self, sh2, in_tmpdir):
        error = sh2.call(['touch', 'touched.txt'])
        assert error == 0
        assert osp.exists('touched.txt')
        assert sh2.stdout_first_line == 'touch touched.txt'

    def test_error(self):
        with pytest.raises(sh.CommandFailed) as exc_info:
            sh.call(['bash', '-c', 'exit 1'])

        assert exc_info.match(r"Command 'bash -c \"exit 1\"' failed with error code 1")

    def test_unchecked(self, sh2):
        error = sh2.call(['bash', '-c', 'exit 1'], check=False)
        assert error == 1
        assert sh2.stdout_first_line == '(bash -c "exit 1") || true'

    def test_command_not_found(self):
        with pytest.raises(sh.CommandNotFound) as exc_info:
            sh.call(['no-such-command', '-lah'], check=False)

        exc_info.match(r"Command 'no-such-command' not found, did you install it\?")

    def test_stderr_to_stdout(self, sh2):
        sh2.call(['bash', '-c', 'echo info'], stderr=subprocess.STDOUT)
        assert sh2.stdout_first_line == 'bash -c "echo info" >&2'


class TestOutput(object):
    def test_echo(self, sh2):
        output = sh2.output(['echo', 'hi'])
        assert sh2.stdout_first_line == '$(echo hi)'
        assert output == 'hi\n'

    def test_error(self):
        with pytest.raises(sh.CommandFailed) as exc_info:
            sh.output(['bash', '-c', 'exit 2'])

        assert exc_info.match(r"Command 'bash -c \"exit 2\"' failed with error code 2")

    def test_unchecked(self, sh2):
        output = sh2.output(['bash', '-c', 'echo before_error; exit 2'], check=False)
        assert output == 'before_error\n'
        assert sh2.stdout_first_line == '$((bash -c "echo before_error; exit 2") || true)'

    def test_stderr_to_stdout(self, sh2):
        output = sh2.output(['bash', '-c', 'echo error >&2'])
        assert output == ''

        output = sh2.output(['bash', '-c', 'echo error >&2'], stderr_to_stdout=True)
        assert output == 'error\n'

    def test_stderr_to_stdout_echo(self, sh2):
        sh2.output(['bash', '-c', 'echo info'], check=False, stderr_to_stdout=True)
        assert sh2.stdout_first_line == '$((bash -c "echo info" >&2) || true)'


class TestPath(object):
    def test_path(self):
        assert sh.path('/usr', 'bin', 'env') == '/usr/bin/env'
        assert sh.path('build', 'lib', 'mollusc') == 'build/lib/mollusc'

    def test_relative(self):
        assert sh.path(os.getcwd(), 'dist', rel=True) == 'dist'
        assert sh.path('/tmp/gnome-software-RSVW9Y', rel='/tmp') == 'gnome-software-RSVW9Y'

    def test_absolute(self):
        assert sh.path('.travis.yml', rel=False) == osp.abspath('.travis.yml')

    def test_unknown_kwarg(self):
        with pytest.raises(TypeError) as exc_info:
            sh.path('.', abs=True)

        exc_info.match(r"Unknown kwargs \['abs'\]")


class TestFileUtil(object):
    def test_remove(self, in_tmpdir):
        os.mkdir('dir')
        sh.write('dir/file', '')
        sh.write('file2', '')

        sh.remove('dir')
        sh.remove([])
        sh.remove(['file2', 'file3'])
        assert not osp.exists('dir')
        assert not osp.exists('file2')

    def test_glob_remove(self, in_tmpdir):
        sh.write('.cache', '')
        sh.write('config', '')
        os.mkdir('build')
        sh.write('build/build.log', '')
        sh.write('build/package.tar.gz', '')

        sh.remove('*')
        assert osp.exists('.cache')
        assert osp.exists('config')
        assert osp.exists('build')

        sh.remove(sh.glob('.*') + sh.glob(sh.path('build', '*.log')))
        assert not osp.exists('.cache')
        assert osp.exists('config')
        assert not osp.exists('build/build.log')
        assert osp.exists('build/package.tar.gz')
