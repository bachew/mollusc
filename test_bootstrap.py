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


def project(method):
    @functools.wraps(method)
    def wrapped(self):
        test_dir = osp.abspath('.test')

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
            print('\n')  # easier to debug
            run(*cmd)

            # glob() ignore hidden files if dot not specified
            pythons = list_dir(proj_dir, '.*/bin/python') + list_dir(proj_dir, '*/bin/python')
            return pythons[0] if pythons else 'python-not-found'

        script_path = osp.abspath(osp.join(osp.dirname(__file__), 'bootstrap'))
        shutil.copy2(script_path, proj_dir)
        # So that bootstrap is not always run from Python 2
        rewrite_shebang(osp.join(proj_dir, 'bootstrap'))

        old_dir = os.getcwd()
        print('cd {!r}'.format(method_dir))
        os.chdir(method_dir)
        try:
            return method(self, osp.relpath(proj_dir), bootstrap)
        finally:
            os.chdir(old_dir)

    return wrapped


project.test_dir_cleared = False


def rewrite_shebang(path):
    with open(path) as f:
        script = f.read()

    python = osp.basename(sys.executable)
    script = script.replace('#!/usr/bin/env python',
                            '#!/usr/bin/env {}'.format(python))

    with open(path, 'w') as f:
        f.write(script)


def list_dir(*path):
    return list(glob(osp.join(*path)))


def write_file(path, content):
    with open(path, 'w') as f:
        f.write(dedent(content))


def run(*cmd, **kwargs):
    cmd = list(cmd)
    capture = kwargs.pop('capture', False)

    if kwargs:
        raise TypeError('Unknown arguments {!r}'.format(kwargs))

    cmdline = subprocess.list2cmdline(cmd)
    print('run:', cmdline)

    if capture:
        output = subprocess.check_output(cmd)
        return output.decode(sys.stdout.encoding or 'utf-8')

    subprocess.check_call(cmd)


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
    def test_pip_install_options(self, proj_dir, bootstrap):
        write_file(osp.join(proj_dir, 'requirements.txt'), '''\
            kerberos==1.2.5
            ''')
        write_file(osp.join(proj_dir, 'bootstrap_config.py'), '''\
            dev = True
            pip_install_options = ['-i', 'https://testpypi.python.org/pypi/']
            ''')
        # kerberos==1.2.5 is not in testpypi
        self.assertRaises(CalledProcessError, bootstrap)

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
            pip_install_options = ['-i', 'https://testpypi.python.org/pypi/']
            ''')
        output = bootstrap_list()
        self.assertTrue("python = 'python2'" in output)
        self.assertTrue("pip_install_options = ['-i', 'https://testpypi.python.org/pypi/']" in output)

        write_file(osp.join(proj_dir, 'bootstrap_config_test.py'), '''\
            import bootstrap_config

            dev = False  # release testing
            pip_install_options = bootstrap_config.pip_install_options + ['-v']
            ''')
        output = bootstrap_list()
        self.assertTrue("python = 'python2'" in output)
        self.assertTrue("dev = False" in output)
        self.assertTrue("pip_install_options = ['-i', 'https://testpypi.python.org/pypi/', '-v']" in output)

        os.remove(osp.join(proj_dir, 'bootstrap_config.py'))
        os.remove(osp.join(proj_dir, 'bootstrap_config_test.py'))
        output = bootstrap_list()
        # Assert no phantom config created by left over pyc files
        self.assertTrue("python = 'python3'" in output)
        self.assertTrue("dev = True" in output)

    @project
    def test_venv_dir(self, proj_dir, bootstrap):
        write_file(osp.join(proj_dir, 'bootstrap_config.py'), '''\
            venv_dir = 'venv'
            ''')
        python = bootstrap()
        self.assertTrue(osp.samefile(osp.join(proj_dir, 'venv/bin/python'), python))

    @project
    def test_post_bootstrap(self, proj_dir, bootstrap):
        write_file(osp.join(proj_dir, 'bootstrap_config.py'), '''\
            def post_bootstrap(**kwargs):
                # Current dir is always project dir
                with open('bootstrap.log', 'a') as f:
                    f.write('Just checking\\n')
            ''')
        write_file(osp.join(proj_dir, 'bootstrap_config_test.py'), '''\
            import bootstrap_config
            from os import path as osp
            from subprocess import check_call


            def post_bootstrap(**kwargs):
                bootstrap_config.post_bootstrap(**kwargs)

                with open('bootstrap.log', 'a') as f:
                    f.write('Install something\\n')

                pip = osp.join(kwargs['venv_dir'], 'bin', 'pip')
                check_call([pip, 'install', 'six'])
            ''')
        bootstrap()

        with open(osp.join(proj_dir, 'bootstrap.log')) as f:
            self.assertEqual(f.read(), 'Just checking\nInstall something\n')
