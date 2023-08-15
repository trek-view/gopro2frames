#!/usr/bin/env python

import io
import os
import sys
import requests
import shutil, platform
from shutil import rmtree
from zipfile import ZipFile, ZIP_DEFLATED

from setuptools import find_packages, setup, Command


# What packages are required for this module to be executed?
REQUIRED = [
    # 'requests',
]

# What packages are optional?
EXTRAS = {
    # 'fancy feature': ['django'],
}

class BootstrapCommand(Command):
    user_options = []
    @staticmethod
    def status(s):
        """Prints things in bold."""
        print('\033[1m{0}\033[0m'.format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):

    if platform.system() == "Windows":
        os.system("cd .\\libs\\fusion2sphere-batch && make")
        os.system("cd .\\libs\\MAX2sphere-batch && make")
    else:
        os.system("cd ./libs/fusion2sphere-batch && make")
        os.system("cd ./libs/MAX2sphere-batch && make")
        sys.exit()

setup(
    name='gopro-frame-maker',
    version='1.0',
    description='Converts GoPro mp4s with equirectangular projections into single frames with correct metadata.',
    cmdclass={
        'bootstrap': BootstrapCommand,
    },
)
