# -*- coding: utf-8 -*-\
import os
import pytest
import subprocess
from mollusc import sh, Shell
from os import path as osp
from pprint import pformat
from six import StringIO
from textwrap import dedent


class Shell2(Shell):
    def __init__(self):
        super(Shell2, self).__init__(StringIO(), StringIO())

    @property
    def stdout_first_line(self):
        return self.stdout.getvalue().splitlines()[0]


@pytest.fixture
def sh2():
    return Shell2()


@pytest.fixture
def tmpdir2(tmpdir):
    with tmpdir.as_cwd():
        yield tmpdir


class TestEcho(object):
    def test_real(self):
        sh.echo('Message')
        sh.echo('Message', error=True)

    def test_stdout_stderr(self, sh2):
        sh2.echo('Message')
        assert sh2.stdout.getvalue() == 'Message\n'
        assert sh2.stderr.getvalue() == ''
        sh2.echo('Error', error=True)
        assert sh2.stdout.getvalue() == 'Message\n'
        assert sh2.stderr.getvalue() == 'Error\n'

    def test_byte_string(self, sh2):
        sh2.echo(u'人'.encode('utf8'))
        assert sh2.stdout.getvalue() == u'人\n'

    def test_line_end(self, sh2):
        sh2.echo('Downloading...', end='')
        assert sh2.stdout.getvalue() == 'Downloading...'
        sh2.echo(' done')
        assert sh2.stdout.getvalue() == 'Downloading... done\n'

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
        assert sh2.stdout.getvalue() == pformat(obj)


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


def test_temp_dir(tmpdir2):
    with sh.temp_dir() as path:
        assert osp.isdir(path)

    assert not osp.exists(path)


class TestChangeDir(object):
    def test_call(self, tmpdir):
        orig_dir = os.getcwd()
        assert osp.samefile(sh.working_dir, orig_dir)
        sh.change_dir(tmpdir.strpath)

        try:
            assert osp.samefile(tmpdir.strpath, os.getcwd())
            assert osp.samefile(tmpdir.strpath, sh.working_dir)
        finally:
            os.chdir(orig_dir)

    def test_context(self, tmpdir):
        with sh.change_dir(tmpdir.strpath):
            assert osp.samefile(tmpdir.strpath, os.getcwd())

    def test_output(self, sh2, tmpdir):
        orig_dir = os.getcwd()

        with sh2.change_dir(tmpdir.strpath):
            pass

        assert sh2.stdout.getvalue() == dedent('''\
            cd {!r}
            cd {!r}  # back from {!r}
            ''').format(tmpdir.strpath, orig_dir, tmpdir.strpath)


def test_change_temp_dir(tmpdir):
    with sh.change_temp_dir() as path:
        assert osp.samefile(path, os.getcwd())

    assert not osp.exists(path)


class TestCall(object):
    def test_touch(self, sh2, tmpdir2):
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
            sh.call(['no-such-command-lah'], check=False)

        exc_info.match(r"Command 'no-such-command-lah' not found, did you install it\?")

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
