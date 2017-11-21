# -*- coding: utf-8 -*-
import errno
import sys
from mollusc import sh, util
from os import path as osp


class VirtualEnv(object):
    def __init__(self, prefix=sys.prefix):
        self.prefix = prefix

    @property
    def site_packages_dir(self):
        return osp.join(self.prefix, 'lib', 'python{}'.format(sys.version[:3]), 'site-packages')

    @property
    def paths_file(self):
        return osp.join(self.site_packages_dir, 'mollusc.pth')

    def add_path(self, path):
        self.add_paths([path])

    def add_paths(self, paths):
        all_paths = self.read_paths()

        for new_path in paths:
            if new_path not in all_paths:
                all_paths.append(new_path)

        self.write_paths(all_paths)

    def read_paths(self):
        paths = []
        try:
            with open(self.paths_file) as f:
                for line in f.readlines():
                    line = line.strip()

                    if line:
                        paths.append(line)
        except IOError as e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise

        return paths

    def write_paths(self, paths):
        sh.echo('Write paths to {!r}'.format(osp.relpath(self.paths_file)))

        with open(self.paths_file, 'w') as f:
            for path in paths:
                if path:
                    f.write(osp.abspath(str(path)))
                    f.write('\n')

    def add_script(self, name, module, function):
        script_file = osp.join(self.prefix, 'bin', name)
        sh.echo('Add script {!r}'.format(osp.relpath(script_file)))
        script = [
            '#!/usr/bin/env python\n',
            'from ', module, ' import ', function, '\n\n',
            function, '()\n'
        ]
        sh.write(script_file, ''.join(script), echo=False)
        sh.chmod_x(script_file, echo=False)


util.make_object_module(locals(), VirtualEnv())
