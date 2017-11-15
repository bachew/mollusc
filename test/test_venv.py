# -*- coding: utf-8 -*-
import os
import pytest
from mollusc._sh import sh
from mollusc._venv import VirtualEnv
from os import path as osp


@pytest.fixture
def venv(tmpdir):
    venv = VirtualEnv(tmpdir.strpath)
    tmpdir.join('bin').ensure_dir()
    os.makedirs(venv.site_packages_dir)
    return venv


def test_read_write_paths(venv):
    assert venv.read_paths() == []
    venv.write_paths(['/a', '/b', '/c'])
    assert venv.read_paths() == ['/a', '/b', '/c']
    venv.write_paths(['/b', '/c', '/d'])
    assert venv.read_paths() == ['/b', '/c', '/d']


def test_write_bad_paths(venv):
    venv.write_paths(['', None, 0, 1])
    paths = venv.read_paths()
    assert len(paths) == 1
    assert paths[0].endswith('/1')


def test_add_paths(venv):
    venv.add_paths(['/w', '/x', '/y'])
    assert venv.read_paths() == ['/w', '/x', '/y']
    venv.add_paths(['/x', '/y', '/z'])
    assert venv.read_paths() == ['/w', '/x', '/y', '/z']


def test_add_path(venv):
    venv.add_path('/u')
    venv.add_path('/v')
    venv.add_path('/v')
    venv.add_path('/w')
    assert venv.read_paths() == ['/u', '/v', '/w']


def test_add_script(venv):
    venv.add_script('unit-test', 'unittest', 'main')
    sh.call([osp.join(venv.prefix, 'bin', 'unit-test')])
