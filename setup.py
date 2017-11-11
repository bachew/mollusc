# -*- coding: utf-8 -*-
from glob import glob
from os import path as osp
from setuptools import setup, find_packages


proj_dir = osp.dirname(__file__)
modules = [osp.splitext(osp.basename(path))[0]
           for path in glob(osp.join(proj_dir, 'src/*.py'))]
config = {
    'name': 'mollusc',
    'version': '0.0.2',
    'description': 'Bootstrap your Python projects',
    'license': 'MIT',
    'author': 'Chew Boon Aik',
    'author_email': 'bachew@gmail.com',
    'url': 'https://github.com/bachew/mollusc',
    'download_url': 'https://github.com/bachew/mollusc/archive/master.zip',
    'packages': find_packages('src'),
    'package_dir': {'': 'src'},
    'py_modules': modules,
    'install_requires': [
        'six>=1.11.0',
    ],
    'zip_safe': False,
    'classifiers': [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Utilities',

    ],
}
setup(**config)
