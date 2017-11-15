# -*- coding: utf-8 -*-
def post_bootstrap(**kwargs):
    from mollusc import venv

    venv.add_path('build-tool')
    venv.add_script('b', 'cli', 'main')
