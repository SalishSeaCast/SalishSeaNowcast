#  Copyright 2013-2019 The Salish Sea MEOPAR contributors
#  and The University of British Columbia
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""SalishSeaNowcast -- Salish Sea NEMO model nowcast system
"""
from setuptools import find_packages, setup

import __pkg_metadata__

python_classifiers = [
    f"Programming Language :: Python :: {py_version}" for py_version in ["3", "3.6"]
]
other_classifiers = [
    "Development Status :: " + __pkg_metadata__.DEV_STATUS,
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: Implementation :: CPython",
    "Operating System :: POSIX :: Linux",
    "Operating System :: Unix",
    "Environment :: Console",
    "Intended Audience :: Science/Research",
    "Intended Audience :: Education",
    "Intended Audience :: Developers",
]
try:
    long_description = open("README.rst", "rt").read()
except IOError:
    long_description = ""
install_requires = [
    # see environment-prod.yaml for conda environment production installation
    # see environment-dev.yaml for conda environment dev installation
    # see requirements.txt for package versions used during recent development
    # see environment-rtd.yaml for conda environment used for readthedocs build
    "angles",
    "basemap",
    "beautifulsoup4",
    "bottleneck",
    "cliff",
    "cmocean",
    "dask",
    "docutils",
    "driftwood",
    "f90nml",
    "feedgen",
    "gsw",
    "lxml",
    "mako",
    "matplotlib",
    "nemo_nowcast",
    "netcdf4",
    "numpy",
    "pandas",
    "paramiko",
    "pillow",
    "poppler",
    "pygrib",
    "pypdf2",
    "pyproj",
    "python-hglib",
    "raven",
    "retrying",
    "scipy",
    "scour",
    "shapely",
    "utm",
    "watchdog",
    "xarray",
    "zeep",
    # 'NEMO_Nowcast',  # use pip install --editable NEMO_Nowcast/
    # 'moad_tools',  # use pip install --editable moad_tools
    # 'SalishSeaTools',  # use pip install --editable SalishSeaTools/
    # 'NEMO-Cmd',  # use pip install --editable NEMO-Cmd/
    # 'SalishSeaCmd',  # use pip install --editable SalishSeaCmd/
    # 'SalishSeaNowcast',  # use pip install -e SalishSeaNowcast/
]

setup(
    name=__pkg_metadata__.PROJECT,
    version=__pkg_metadata__.VERSION,
    description=__pkg_metadata__.DESCRIPTION,
    long_description=long_description,
    author="Doug Latornell",
    author_email="dlatornell@eoas.ubc.ca",
    url="https://salishsea-nowcast.readthedocs.io/en/latest/",
    license="Apache License, Version 2.0",
    classifiers=python_classifiers + other_classifiers,
    platforms=["MacOS X", "Linux"],
    install_requires=install_requires,
    packages=find_packages(),
)
