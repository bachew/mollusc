#!/bin/bash -e
python2 -m unittest -v test_bootstrap
python3 -m unittest -v test_bootstrap
./bootstrap dev build deploy-wheel -u bachew deploy-doc
