#!/bin/bash -e
python2 test_bootstrap.py
python3 test_bootstrap.py
./bootstrap dev test build deploy-wheel -u bachew deploy-doc
