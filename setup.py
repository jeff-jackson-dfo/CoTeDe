#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Licensed under a 3-clause BSD style license - see LICENSE.rst


import sys
from setuptools import setup

setup(
    packages=[
        'cotede',
        'cotede.qctests',
        'cotede.utils',
        'cotede.humanqc',
        'cotede.anomaly_detection',
        'cotede.fuzzy',
        'cotede.qc_cfg',
    ],
    package_dir = {'cotede': 'cotede'},
)
