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
from unittest import main, TestCase


BASE_DIR = osp.abspath(osp.dirname(__file__))


def project(name):
    def decorator(method):
        @functools.wraps(method)
        def wrapped(test_case):
            run_test(test_case, method, name)

        return wrapped

    return decorator


def run_test(test_case, method, project_name):
    py_version = '.'.join([str(c) for c in sys.version_info[:3]])
    test_dir = osp.join(BASE_DIR, '.test_bootstrap')

    # XXX: Explicit because cache is disabled by default in Debian 8 Pip 9.0.1
    os.environ['PIP_DOWNLOAD_CACHE'] = osp.join(test_dir, 'pip-cache')

    test_py_dir = osp.join(test_dir, 'py{}'.format(py_version))

    # Clear once per test run
    if not run_test.test_py_dir_cleared and osp.exists(test_py_dir):
        for method_dir in glob(osp.join(test_py_dir, '*')):
            shutil.rmtree(method_dir)
        run_test.test_py_dir_cleared = True

    method_dir = osp.join(test_py_dir, method.__name__)
    project_dir = osp.join(method_dir, project_name)
    os.makedirs(project_dir)

    def bootstrap(*args):
        cmd = [osp.join(project_dir, 'bootstrap')]

        if '-p' not in args:
            cmd.append('-p')
            cmd.append(sys.executable)

        cmd.extend(args)
        print('\n# bootstrap')  # easier to debug
        run(*cmd)

        pythons = list_dir(project_dir, '.*-py*/bin/python')
        return pythons[0] if pythons else 'python-not-found'

    shutil.copy2(osp.join(BASE_DIR, 'bootstrap'), project_dir)

    old_dir = os.getcwd()
    print('cd {!r}'.format(method_dir))
    os.chdir(method_dir)
    try:
        return method(test_case, bootstrap)
    finally:
        os.chdir(old_dir)


run_test.test_py_dir_cleared = False


def list_dir(*path):
    return list(glob(osp.join(*path)))


def write(path, content):
    with open(path, 'w') as f:
        f.write(dedent(content))


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

    @project('empty')
    def test_empty(self, bootstrap):
        bootstrap('-l')
        self.assertFalse(list_dir('empty/.empty-*'))
        bootstrap()
        self.assertTrue(list_dir('empty/.empty-*'))

    @project('setup')
    def test_setup_py(self, bootstrap):
        write('setup/README.md', '''\
            # Test setup.py

            `read.py` can only read me in development mode.
            ''')
        write('setup/setup.py', '''\
            from setuptools import find_packages, setup
            setup(
                name='test',
                version='0.0.1',
                py_modules=['read'])
            ''')
        write('setup/read.py', '''\
            from os import path as osp

            with open(osp.join(osp.dirname(__file__), 'README.md')) as f:
                f.read()
            ''')
        python = bootstrap('--dev', '0')
        self.assertRaises(CalledProcessError, run, python, '-m', 'read')

        python = bootstrap()
        run(python, '-m', 'read')

    @project('reqs')
    def test_requirements(self, bootstrap):
        write('reqs/requirements.txt', '''\
            six
            ''')

        python = bootstrap('--dev', '0')
        self.assertRaises(CalledProcessError, run, python, '-c', 'import six')

        python = bootstrap()
        run(python, '-c', 'import six')

    @project('clean')
    def test_clean(self, bootstrap):
        write('clean/requirements.txt', '''\
            six
            ''')

        python = bootstrap()
        run(python, '-c', 'import six')

        os.remove('clean/requirements.txt')
        python = bootstrap()
        run(python, '-c', 'import six')

        python = bootstrap('--clean')
        self.assertRaises(CalledProcessError, run, python, '-c', 'import six')

    @project('insider')
    def test_inside_venv(self, bootstrap):
        os.chdir('insider')
        write('bootstrap.sh', '''\
            set -ex
            ./bootstrap
            source .insider-py*/bin/activate
            ./bootstrap
            ''')
        run('bash', 'bootstrap.sh')

    @project('pipconf')
    def test_pip_config(self, bootstrap):
        write('pipconf/bootstrap_config.py', '''\
            dev = True
            pip_config = {
            }
            ''')
        bootstrap()
        self.assertTrue('pipconf/.pipconf-py*/pip.conf')

        write('pipconf/bootstrap_config.py', '''\
            dev = True
            pip_config = {
                'global': {
                    'index-url': 'https://testpypi.python.org/pypi/'
                }
            }
            ''')
        write('pipconf/requirements.txt', '''\
            kerberos==1.2.5
            ''')
        # kerberos==1.2.5 is not in testpypi
        self.assertRaises(CalledProcessError, bootstrap)

    @project('pipconf')
    def test_pip_config_clean(self, bootstrap):
        def pip_config_exists():
            return bool(list_dir('pipconf/.pipconf-py*/pip.conf'))

        bootstrap()
        self.assertFalse(pip_config_exists())

        write('pipconf/bootstrap_config.py', '''\
            dev = True
            pip_config = {
            }
            ''')
        bootstrap()
        self.assertTrue(pip_config_exists())

        write('pipconf/bootstrap_config.py', '''\
            dev = True
            ''')
        bootstrap()
        self.assertFalse(pip_config_exists())

    @project('config')
    def test_config(self, bootstrap):
        def bootstrap_list():
            output = run('config/bootstrap', '-l', capture=True)
            print(output)
            print('--- capture end ---')
            return output

        output = bootstrap_list()
        self.assertTrue("python = 'python3'" in output)
        self.assertTrue("dev = True" in output)

        write('config/bootstrap_config.py', '''\
            python = 'python2'
            description = 'Configurable bootstrap'
            ''')
        output = bootstrap_list()
        self.assertTrue("python = 'python2'" in output)
        self.assertTrue("description = 'Configurable bootstrap'" in output)

        write('config/bootstrap_config_test.py', '''\
            import bootstrap_config

            dev = False  # release testing
            description = 'Configurable bootstrap (test)'
            ''')
        output = bootstrap_list()
        self.assertTrue("python = 'python2'" in output)
        self.assertTrue("dev = False" in output)
        self.assertTrue("description = 'Configurable bootstrap (test)'" in output)

        os.remove('config/bootstrap_config.py')
        os.remove('config/bootstrap_config_test.py')
        output = bootstrap_list()
        # Assert no phantom config created by left over pyc files
        self.assertTrue("python = 'python3'" in output)
        self.assertTrue("dev = True" in output)

    @project('postboot')
    def test_post_bootstrap(self, bootstrap):
        write('postboot/bootstrap_config.py', '''\
            def post_bootstrap(**kwargs):
                with open('bootstrap.log', 'a') as f:
                    f.write('post_bootstrap(dev={!r})\\n'.format(kwargs['dev']))
            ''')
        write('postboot/bootstrap_config_test.py', '''\
            import bootstrap_config

            dev = False

            def post_bootstrap(**kwargs):
                bootstrap_config.post_bootstrap(**kwargs)

                with open('bootstrap.log', 'a') as f:
                    f.write('post_bootstrap2(dev={!r})\\n'.format(kwargs['dev']))
            ''')
        bootstrap()

        with open('postboot/bootstrap.log') as f:
            exp_log = (
                "post_bootstrap(dev=False)\n"
                "post_bootstrap2(dev=False)\n"
            )
            self.assertEqual(exp_log, f.read())

    @project('dynareqs')
    def test_dynamic_requirements(self, bootstrap):
        write('dynareqs/requirements.txt', '''\
            py
            ''')
        write('dynareqs/bootstrap_config.py', '''\
            from subprocess import check_call

            python='python2'

            def post_bootstrap(**kwargs):
                import py

                check_call(['pip', 'install', 'pytest'])
                import pytest
            ''')
        bootstrap()
        self.assertTrue(list_dir('dynareqs/.*-py*/bin/pytest'))

    @project('runcmd')
    def test_run_command(self, bootstrap):
        write('runcmd/requirements.txt', '''\
            py
            ''')
        bootstrap('python', '-c', "import py; py.path.local('marker').write('')")
        self.assertTrue(osp.exists('marker'))

    @project('sh')
    def test_shells(self, bootstrap):
        bootstrap()
        shells = ['bash']
        # TODO: shells = ['bash', 'csh', 'fish', 'zsh']

        for name in shells:
            bootstrap('-s', name)

    @project('dev')
    def test_dev_script(self, bootstrap):
        write('dev/setup.py', '''\
            from setuptools import find_packages, setup
            setup(
                name='dev',
                version='0.0.1',
                packages=find_packages('src'),
                package_dir={'': 'src'})
            ''')
        write('dev/requirements.txt', '''\
            {}
            click
            '''.format(BASE_DIR))

        write('dev/dev.py', '''\
            import click
            import os
            from mollusc import sh
            from os import path as osp


            @click.command()
            def build_wheel():
                os.chdir(osp.dirname(__file__))
                sh.call(['python', 'setup.py', 'bdist_wheel'])
            ''')

        os.makedirs('dev/src')
        write('dev/src/chicken_and_egg.py', '')

        write('dev/bootstrap_config.py', '''\
            def post_bootstrap(**kwargs):
                import chicken_and_egg
                from mollusc import venv

                venv.add_path('.')
                venv.add_script('build-wheel', 'dev', 'build_wheel')
            ''')
        bootstrap('--clean', 'build-wheel')
        self.assertTrue(list_dir('dev/dist/dev-0.0.1*.whl'))

    @project('cmdsh')
    def test_run_command_and_shell(self, bootstrap):
        bootstrap('-s', 'bash', 'touch', 'x')
        assert osp.exists('x')

    @project('novenv')
    def test_no_venv_option(self, bootstrap):
        self.assertRaises(CalledProcessError, bootstrap, '-ns', 'bash', 'touch', 'y')


if __name__ == '__main__':
    main()
