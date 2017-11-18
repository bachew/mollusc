# -*- coding: utf-8 -*-
from __future__ import print_function
import functools
import os
import subprocess
import shutil
import sys
from glob import glob
from os import path as osp
from subprocess import CalledProcessError
from textwrap import dedent
from unittest import TestCase


BASE_DIR = osp.abspath(osp.dirname(__file__))


# Cache is disabled by default in Debian 8 Pip 9.0.1
# TODO: check that this is not happening elsewhere
os.environ['PIP_DOWNLOAD_CACHE'] = osp.join(BASE_DIR, '.pip-cache')


def project(method):
    @functools.wraps(method)
    def wrapped(test_case):
        test_dir = osp.join(BASE_DIR, '.bootstrap-test')

        # Clear once per test run
        if not project.test_dir_cleared and osp.exists(test_dir):
            for method_dir in glob(osp.join(test_dir, '*')):
                shutil.rmtree(method_dir)
            project.test_dir_cleared = True

        method_dir = osp.join(test_dir, method.__name__)
        proj_dir = osp.join(method_dir, 'proj')
        os.makedirs(proj_dir)

        def bootstrap(*args):
            cmd = [osp.join(proj_dir, 'bootstrap')]

            if '-p' not in args:
                cmd.append('-p')
                cmd.append(sys.executable)

            cmd.extend(args)
            print('\n# bootstrap')  # easier to debug
            run(*cmd)

            # glob() ignore hidden files if .* is not specified
            pythons = list_dir(proj_dir, '.*/bin/python') + list_dir(proj_dir, '*/bin/python')
            return pythons[0] if pythons else 'python-not-found'

        script_path = osp.abspath(osp.join(osp.dirname(__file__), 'bootstrap'))
        shutil.copy2(script_path, proj_dir)

        old_dir = os.getcwd()
        print('cd {!r}'.format(method_dir))
        os.chdir(method_dir)
        try:
            return method(test_case, osp.relpath(proj_dir), bootstrap)
        finally:
            os.chdir(old_dir)

    return wrapped


project.test_dir_cleared = False


def list_dir(*path):
    return list(glob(osp.join(*path)))


def write_file(path, content):
    with open(path, 'w') as f:
        f.write(dedent(content))


def read_file(path):
    with open(path) as f:
        return f.read()


def run(*cmd, **kwargs):
    cmd = list(cmd)
    capture = kwargs.pop('capture', False)

    if kwargs:
        raise TypeError('Unknown arguments {!r}'.format(kwargs))

    cmdline = subprocess.list2cmdline(cmd)
    print(cmdline)

    with open(os.devnull) as stdin:
        kwargs['stdin'] = stdin

        if capture:
            output = subprocess.check_output(cmd, **kwargs)
            return output.decode(sys.stdout.encoding or 'utf-8')

        subprocess.check_call(cmd, **kwargs)


class Test(TestCase):
    @classmethod
    def setUpClass(cls):
        if cls.in_venv():
            raise AssertionError('{} should not be run inside virtual environment'.format(__name__))

    @classmethod
    def in_venv(cls):
        sys_version = sys.version.lower()

        if 'conda' in sys_version or 'continuum' in sys_version:
            return True

        base_prefix = getattr(sys, 'real_prefix', None) or getattr(sys, 'base_prefix', sys.prefix)
        return base_prefix != sys.prefix

    @project
    def test_empty(self, proj_dir, bootstrap):
        bootstrap('-l')
        assert not list_dir(proj_dir, '.proj-*')
        bootstrap()
        assert list_dir(proj_dir, '.proj-*')

    @project
    def test_setup_py(self, proj_dir, bootstrap):
        write_file(osp.join(proj_dir, 'README.md'), '''\
            # Test setup.py

            `read.py` can only read me in development mode.
            ''')
        write_file(osp.join(proj_dir, 'setup.py'), '''\
            from setuptools import find_packages, setup
            setup(
                name='test',
                version='0.0.1',
                py_modules=['read'])
            ''')
        write_file(osp.join(proj_dir, 'read.py'), '''\
            from os import path as osp

            with open(osp.join(osp.dirname(__file__), 'README.md')) as f:
                f.read()
            ''')
        python = bootstrap('--dev', '0')
        self.assertRaises(CalledProcessError, run, python, '-m', 'read')

        python = bootstrap()
        run(python, '-m', 'read')

    @project
    def test_requirements_txt(self, proj_dir, bootstrap):
        write_file(osp.join(proj_dir, 'requirements.txt'), '''\
            six
            ''')

        python = bootstrap('--dev', '0')
        self.assertRaises(CalledProcessError, run, python, '-c', 'import six')

        python = bootstrap()
        run(python, '-c', 'import six')

    @project
    def test_clean(self, proj_dir, bootstrap):
        write_file(osp.join(proj_dir, 'requirements.txt'), '''\
            six
            ''')

        python = bootstrap()
        run(python, '-c', 'import six')

        os.remove(osp.join(proj_dir, 'requirements.txt'))
        python = bootstrap()
        run(python, '-c', 'import six')

        python = bootstrap('--clean')
        self.assertRaises(CalledProcessError, run, python, '-c', 'import six')

    @project
    def test_inside_venv(self, proj_dir, bootstrap):
        os.chdir(proj_dir)
        write_file('bootstrap.sh', '''\
            set -ex
            ./bootstrap
            source .proj-py*/bin/activate
            ./bootstrap
            ''')
        run('bash', 'bootstrap.sh')

    @project
    def test_pip_config(self, proj_dir, bootstrap):
        write_file(osp.join(proj_dir, 'bootstrap_config.py'), '''\
            dev = True
            pip_config = {
            }
            ''')
        bootstrap()
        self.assertTrue(list_dir(proj_dir, '.proj-py*', 'pip.conf'))

        write_file(osp.join(proj_dir, 'bootstrap_config.py'), '''\
            dev = True
            pip_config = {
                'global': {
                    'index-url': 'https://testpypi.python.org/pypi/'
                }
            }
            ''')
        write_file(osp.join(proj_dir, 'requirements.txt'), '''\
            kerberos==1.2.5
            ''')
        # kerberos==1.2.5 is not in testpypi
        self.assertRaises(CalledProcessError, bootstrap)

    @project
    def test_remove_pip_config(self, proj_dir, bootstrap):
        def pip_config_exists():
            return bool(list_dir(proj_dir, '.proj-py*', 'pip.conf'))

        bootstrap()
        self.assertFalse(pip_config_exists())

        write_file(osp.join(proj_dir, 'bootstrap_config.py'), '''\
            dev = True
            pip_config = {
            }
            ''')
        bootstrap()
        self.assertTrue(pip_config_exists())

        write_file(osp.join(proj_dir, 'bootstrap_config.py'), '''\
            dev = True
            ''')
        bootstrap()
        self.assertFalse(pip_config_exists())

    @project
    def test_config(self, proj_dir, bootstrap):
        def bootstrap_list():
            bootstrap_script = osp.join(proj_dir, 'bootstrap')
            output = run(bootstrap_script, '-l', capture=True)
            print(output)
            print('--- capture end ---')
            return output

        output = bootstrap_list()
        self.assertTrue("python = 'python3'" in output)
        self.assertTrue("dev = True" in output)

        write_file(osp.join(proj_dir, 'bootstrap_config.py'), '''\
            python = 'python2'
            description = 'Configurable bootstrap'
            ''')
        output = bootstrap_list()
        self.assertTrue("python = 'python2'" in output)
        self.assertTrue("description = 'Configurable bootstrap'" in output)

        write_file(osp.join(proj_dir, 'bootstrap_config_test.py'), '''\
            import bootstrap_config

            dev = False  # release testing
            description = 'Configurable bootstrap (test)'
            ''')
        output = bootstrap_list()
        self.assertTrue("python = 'python2'" in output)
        self.assertTrue("dev = False" in output)
        self.assertTrue("description = 'Configurable bootstrap (test)'" in output)

        os.remove(osp.join(proj_dir, 'bootstrap_config.py'))
        os.remove(osp.join(proj_dir, 'bootstrap_config_test.py'))
        output = bootstrap_list()
        # Assert no phantom config created by left over pyc files
        self.assertTrue("python = 'python3'" in output)
        self.assertTrue("dev = True" in output)

    @project
    def test_post_bootstrap(self, proj_dir, bootstrap):
        write_file(osp.join(proj_dir, 'bootstrap_config.py'), '''\
            def post_bootstrap(**kwargs):
                with open('bootstrap.log', 'a') as f:
                    f.write('post_bootstrap(dev={!r})\\n'.format(kwargs['dev']))
            ''')
        write_file(osp.join(proj_dir, 'bootstrap_config_test.py'), '''\
            import bootstrap_config

            dev = False

            def post_bootstrap(**kwargs):
                bootstrap_config.post_bootstrap(**kwargs)

                with open('bootstrap.log', 'a') as f:
                    f.write('post_bootstrap2(dev={!r})\\n'.format(kwargs['dev']))
            ''')
        bootstrap()

        with open(osp.join(proj_dir, 'bootstrap.log')) as f:
            exp_log = (
                "post_bootstrap(dev=False)\n"
                "post_bootstrap2(dev=False)\n"
            )
            self.assertEqual(exp_log, f.read())

    @project
    def test_dynamic_requirements(self, proj_dir, bootstrap):
        write_file(osp.join(proj_dir, 'requirements.txt'), '''\
            py
            ''')
        write_file(osp.join(proj_dir, 'bootstrap_config.py'), '''\
            from subprocess import check_call

            python='python2'

            def post_bootstrap(**kwargs):
                import py

                check_call(['pip', 'install', 'pytest'])
                import pytest
            ''')
        python = bootstrap()
        pytest = osp.join(osp.dirname(python), 'pytest')
        assert osp.exists(pytest)

    @project
    def test_run_command(self, proj_dir, bootstrap):
        write_file(osp.join(proj_dir, 'requirements.txt'), '''\
            py
            ''')
        bootstrap('python', '-c', "import py; py.path.local('marker').write('')")
        self.assertTrue(osp.exists('marker'))

    @project
    def test_shells(self, proj_dir, bootstrap):
        bootstrap()
        shells = ['bash']
        # TODO: shells = ['bash', 'csh', 'fish', 'zsh']

        for name in shells:
            bootstrap('-s', name)

    @project
    def test_dev_script(self, proj_dir, bootstrap):
        write_file(osp.join(proj_dir, 'setup.py'), '''\
            from setuptools import find_packages, setup
            setup(
                name='testproj',
                version='0.0.1',
                packages=find_packages('src'),
                package_dir={'': 'src'})
            ''')
        write_file(osp.join(proj_dir, 'requirements.txt'), '''\
            {}
            click
            '''.format(BASE_DIR))

        dev_dir = osp.join(proj_dir, 'dev')
        os.makedirs(dev_dir)
        write_file(osp.join(dev_dir, 'cli.py'), '''\
            import click
            import os
            from mollusc import sh
            from os import path as osp


            @click.command()
            def build_wheel():
                project_dir = sh.abspath(osp.dirname(__file__), '..')
                os.chdir(project_dir)
                sh.call(['python', 'setup.py', 'bdist_wheel'])
            ''')

        src_dir = osp.join(proj_dir, 'src')
        os.makedirs(src_dir)
        write_file(osp.join(src_dir, 'chicken_and_egg.py'), '')

        write_file(osp.join(proj_dir, 'bootstrap_config.py'), '''\
            def post_bootstrap(**kwargs):
                import chicken_and_egg
                from mollusc import venv

                venv.add_path('dev')
                venv.add_script('build-wheel', 'cli', 'build_wheel')
            ''')
        bootstrap('--clean', 'build-wheel')
        self.assertTrue(list_dir(proj_dir, 'dist', 'testproj-0.0.1*.whl'))

    @project
    def test_run_command_and_shell(self, proj_dir, bootstrap):
        bootstrap('-s', 'bash', 'touch', 'x')
        assert osp.exists('x')

    @project
    def test_no_venv_option(self, proj_dir, bootstrap):
        self.assertRaises(CalledProcessError, bootstrap, '-ns', 'bash', 'touch', 'y')
