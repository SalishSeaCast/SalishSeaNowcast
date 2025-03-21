..  Copyright 2013 – present by the SalishSeaCast Project contributors
..  and The University of British Columbia
..
..  Licensed under the Apache License, Version 2.0 (the "License");
..  you may not use this file except in compliance with the License.
..  You may obtain a copy of the License at
..
..     https://www.apache.org/licenses/LICENSE-2.0
..
..  Unless required by applicable law or agreed to in writing, software
..  distributed under the License is distributed on an "AS IS" BASIS,
..  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
..  See the License for the specific language governing permissions and
..  limitations under the License.

.. SPDX-License-Identifier: Apache-2.0


.. _SalishSeaNowcastPackagedDevelopment:

****************************************
``SalishSeaNowcast`` Package Development
****************************************

+----------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **Continuous Integration** | .. image:: https://github.com/SalishSeaCast/SalishSeaNowcast/actions/workflows/pytest-with-coverage.yaml/badge.svg                                                                                       |
|                            |      :target: https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:pytest-with-coverage                                                                                              |
|                            |      :alt: Pytest with Coverage Status                                                                                                                                                                   |
|                            | .. image:: https://codecov.io/gh/SalishSeaCast/SalishSeaNowcast/branch/main/graph/badge.svg                                                                                                              |
|                            |      :target: https://app.codecov.io/gh/SalishSeaCast/SalishSeaNowcast                                                                                                                                   |
|                            |      :alt: Codecov Testing Coverage Report                                                                                                                                                               |
|                            | .. image:: https://github.com/SalishSeaCast/SalishSeaNowcast/actions/workflows/codeql-analysis.yaml/badge.svg                                                                                            |
|                            |      :target: https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:CodeQL                                                                                                            |
|                            |      :alt: CodeQL analysis                                                                                                                                                                               |
+----------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **Documentation**          | .. image:: https://readthedocs.org/projects/salishsea-nowcast/badge/?version=latest                                                                                                                      |
|                            |      :target: https://salishsea-nowcast.readthedocs.io/en/latest/                                                                                                                                        |
|                            |      :alt: Documentation Status                                                                                                                                                                          |
|                            | .. image:: https://github.com/SalishSeaCast/SalishSeaNowcast/actions/workflows/sphinx-linkcheck.yaml/badge.svg                                                                                           |
|                            |      :target: https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:sphinx-linkcheck                                                                                                  |
|                            |      :alt: Sphinx linkcheck                                                                                                                                                                              |
+----------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **Package**                | .. image:: https://img.shields.io/github/v/release/SalishSeaCast/SalishSeaNowcast?logo=github                                                                                                            |
|                            |      :target: https://github.com/SalishSeaCast/SalishSeaNowcast/releases                                                                                                                                 |
|                            |      :alt: Releases                                                                                                                                                                                      |
|                            | .. image:: https://img.shields.io/python/required-version-toml?tomlFilePath=https://raw.githubusercontent.com/SalishSeaCast/SalishSeaNowcast/main/pyproject.toml&logo=Python&logoColor=gold&label=Python |
|                            |      :target: https://docs.python.org/3/                                                                                                                                                                 |
|                            |      :alt: Python Version from PEP 621 TOML                                                                                                                                                              |
|                            | .. image:: https://img.shields.io/github/issues/SalishSeaCast/SalishSeaNowcast?logo=github                                                                                                               |
|                            |      :target: https://github.com/SalishSeaCast/SalishSeaNowcast/issues                                                                                                                                   |
|                            |      :alt: Issue Tracker                                                                                                                                                                                 |
+----------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **Meta**                   | .. image:: https://img.shields.io/badge/license-Apache%202-cb2533.svg                                                                                                                                    |
|                            |      :target: https://www.apache.org/licenses/LICENSE-2.0                                                                                                                                                |
|                            |      :alt: Licensed under the Apache License, Version 2.0                                                                                                                                                |
|                            | .. image:: https://img.shields.io/badge/version%20control-git-blue.svg?logo=github                                                                                                                       |
|                            |      :target: https://github.com/SalishSeaCast/SalishSeaNowcast                                                                                                                                          |
|                            |      :alt: Git on GitHub                                                                                                                                                                                 |
|                            | .. image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white                                                                                                  |
|                            |      :target: https://pre-commit.com                                                                                                                                                                     |
|                            |      :alt: pre-commit                                                                                                                                                                                    |
|                            | .. image:: https://img.shields.io/badge/code%20style-black-000000.svg                                                                                                                                    |
|                            |      :target: https://black.readthedocs.io/en/stable/                                                                                                                                                    |
|                            |      :alt: The uncompromising Python code formatter                                                                                                                                                      |
|                            | .. image:: https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg                                                                                                                                    |
|                            |      :target: https://github.com/pypa/hatch                                                                                                                                                              |
|                            |      :alt: Hatch project                                                                                                                                                                                 |
+----------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

The ``SalishSeaNowcast`` package is a collection of Python modules associated with
running the SalishSeaCast ocean models in a daily nowcast/forecast mode.
The package uses the `NEMO_Nowcast`_ framework to implement the :ref:`SalishSeaNowcastSystem`.

.. _NEMO_Nowcast: https://nemo-nowcast.readthedocs.io/en/latest/


.. _SalishSeaNowcastPythonVersions:

Python Version
==============

.. image:: https://img.shields.io/python/required-version-toml?tomlFilePath=https://raw.githubusercontent.com/SalishSeaCast/SalishSeaNowcast/main/pyproject.toml&logo=Python&logoColor=gold&label=Python
     :target: https://docs.python.org/3/
     :alt: Python Version from PEP 621 TOML

The ``SalishSeaNowcast`` package is developed and tested using `Python`_ 3.13.

.. _Python: https://www.python.org/


.. _SalishSeaNowcastGettingTheCode:

Getting the Code
================

.. image:: https://img.shields.io/badge/version%20control-git-blue.svg?logo=github
    :target: https://github.com/SalishSeaCast/SalishSeaNowcast
    :alt: Git on GitHub

Clone the code and documentation `repository`_ from GitHub with:

.. _repository: https://github.com/SalishSeaCast/SalishSeaNowcast

.. code-block:: bash

    $ git clone git@github.com:SalishSeaCast/SalishSeaNowcast.git


.. _SalishSeaNowcastDevelopmentEnvironment:

Development Environment
=======================

Setting up an isolated development environment using `Conda`_ is recommended.
Assuming that you have `Miniconda`_ installed,
you can create and activate an environment called ``salishsea-nowcast`` that will have all of the Python packages necessary for development,
testing,
and building the documentation with the commands below.

.. _Conda: https://docs.conda.io/en/latest/
.. _Miniconda: https://docs.conda.io/en/latest/miniconda.html

``SalishSeaNowcast`` depends on a collection of other Python packages developed by the SalishSeaCast project and friends:

* `NEMO_Nowcast`_
* `moad_tools`_
* `Reshapr`_
* :ref:`SalishSeaToolsPackage`
* `OPPTools`_
* `NEMO-Cmd`_
* :ref:`SalishSeaCmdProcessor`
* `FVCOM-Cmd`_

.. _moad_tools: https://ubc-moad-tools.readthedocs.io/en/latest/index.html
.. _Reshapr: https://reshapr.readthedocs.io/en/latest/index.html
.. _OPPTools: https://gitlab.com/mdunphy/OPPTools
.. _NEMO-Cmd: https://nemo-cmd.readthedocs.io/en/latest/
.. _FVCOM-Cmd: https://github.com/SalishSeaCast/FVCOM-Cmd

If you have not done so already,
you can clone those repos with:

.. code-block:: bash

    $ cd SalishSeaNowcast/..
    $ git clone git@github.com:43ravens/NEMO_Nowcast.git
    $ git clone git@github.com:UBC-MOAD/moad_tools.git
    $ git clone git@github.com:UBC-MOAD/Reshapr.git
    $ git clone git@github.com:SalishSeaCast/tools.git
    $ git clone git@gitlab.com:douglatornell/OPPTools.git
    $ git clone git@github.com:SalishSeaCast/NEMO-Cmd.git
    $ git clone git@github.com:SalishSeaCast/SalishSeaCmd.git
    $ git clone git@github.com:SalishSeaCast/FVCOM-Cmd.git

If you already have clones of those repos,
please ensure that they are up to date.

Assuming that those repos are cloned beside your ``SalishSeaNowcast`` clone,
the commands below install the packages into your ``salishsea-nowcast`` development environment.

.. code-block:: bash

    $ cd SalishSeaNowcast
    $ conda env create -f envs/environment-dev.yaml
    $ conda activate salishsea-nowcast
    (salishsea-nowcast)$ python -m pip install --editable ../NEMO_Nowcast
    (salishsea-nowcast)$ python -m pip install --editable ../moad_tools
    (salishsea-nowcast)$ python -m pip install --editable ../Reshapr
    (salishsea-nowcast)$ python -m pip install --editable ../tools/SalishSeaTools
    (salishsea-nowcast)$ cd ../OPPTools
    (salishsea-nowcast)$ git switch SalishSeaCast-prod
    (salishsea-nowcast)$ cd ../SalishSeaNowcast
    (salishsea-nowcast)$ python -m pip install --editable OPPTools
    (salishsea-nowcast)$ python -m pip install --editable ../NEMO-Cmd
    (salishsea-nowcast)$ python -m pip install --editable ../SalishSeaCmd
    (salishsea-nowcast)$ python -m pip install --editable ../FVCOM-Cmd
    (salishsea-nowcast)$ python -m pip install --editable .

The ``--editable`` option in the :command:`pip install` command above installs the packages from the cloned repos via symlinks so that the installed packages will be automatically updated as the repos evolve.

To deactivate the environment use:

.. code-block:: bash

    (salishsea-nowcast)$ conda deactivate


.. _SalishSeaNowcastCodingStyle:

Coding Style
============

.. image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
   :target: https://pre-commit.com
   :alt: pre-commit
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://black.readthedocs.io/en/stable/
    :alt: The uncompromising Python code formatter

The ``SalishSeaNowcast`` package uses Git pre-commit hooks managed by `pre-commit`_
to maintain consistent code style and and other aspects of code,
docs,
and repo QA.

.. _pre-commit: https://pre-commit.com/

To install the `pre-commit` hooks in a newly cloned repo,
activate the conda development environment,
and run :command:`pre-commit install`:

.. code-block:: bash

    $ cd SalishSeaNowcast
    $ conda activate salishsea-nowcast
    (salishsea-nowcast)$ pre-commit install

.. note::
    You only need to install the hooks once immediately after you make a new clone of the
    `SalishSeaNowcast repository`_ and build your :ref:`SalishSeaNowcastDevelopmentEnvironment`.

.. _SalishSeaNowcast repository: https://github.com/SalishSeaCast/SalishSeaNowcast


.. _SalishSeaNowcastBuildingTheDocumentation:

Building the Documentation
==========================

.. image:: https://readthedocs.org/projects/salishsea-nowcast/badge/?version=latest
    :target: https://salishsea-nowcast.readthedocs.io/en/latest/
    :alt: Documentation Status

The documentation for the ``SalishSeaNowcast`` package is written in `reStructuredText`_ and converted to HTML using `Sphinx`_.
Creating a :ref:`SalishSeaNowcastDevelopmentEnvironment` as described above includes the installation of Sphinx.
Building the documentation is driven by the :file:`docs/Makefile`.
With your ``salishsea-nowcast`` development environment activated,
use:

.. _reStructuredText: https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
.. _Sphinx: https://www.sphinx-doc.org/en/master/

.. code-block:: bash

    (salishsea-nowcast)$ (cd docs && make clean html)

to do a clean build of the documentation.
The output looks something like:

.. code-block:: text

    Removing everything under '_build'...
    Running Sphinx v8.1.3
    loading translations [en]... done
    making output directory... done
    loading intersphinx inventory 'python' from https://docs.python.org/3/objects.inv ...
    loading intersphinx inventory 'nemonowcast' from https://nemo-nowcast.readthedocs.io/en/latest/objects.inv ...
    loading intersphinx inventory 'salishseadocs' from https://salishsea-meopar-docs.readthedocs.io/en/latest/objects.inv ...
    loading intersphinx inventory 'salishseatools' from https://salishsea-meopar-tools.readthedocs.io/en/latest/objects.inv ...
    loading intersphinx inventory 'salishseasite' from https://salishsea-site.readthedocs.io/objects.inv ...
    loading intersphinx inventory 'salishseacmd' from https://salishseacmd.readthedocs.io/en/latest/objects.inv ...
    building [mo]: targets for 0 po files that are out of date
    writing output...
    building [html]: targets for 20 source files that are out of date
    updating environment: [new config] 20 added, 0 changed, 0 removed
    reading sources... [100%] workers
    looking for now-outdated files... none found
    pickling environment... done
    checking consistency... done
    preparing documents... done
    copying assets...
    copying static files...
    Writing evaluated template result to /media/doug/warehouse/MEOPAR/SalishSeaNowcast/docs/_build/html/_static/language_data.js
    Writing evaluated template result to /media/doug/warehouse/MEOPAR/SalishSeaNowcast/docs/_build/html/_static/basic.css
    Writing evaluated template result to /media/doug/warehouse/MEOPAR/SalishSeaNowcast/docs/_build/html/_static/documentation_options.js
    Writing evaluated template result to /media/doug/warehouse/MEOPAR/SalishSeaNowcast/docs/_build/html/_static/js/versions.js
    copying static files: done
    copying extra files...
    copying extra files: done
    copying assets: done
    writing output... [100%] workers
    generating indices... genindex py-modindex done
    highlighting module code... [100%] nowcast.workers.watch_ww3
    writing additional pages... search done
    copying images... [100%] ProcessFlow.png
    dumping search index in English (code: en)... done
    dumping object inventory... done
    build succeeded.

    The HTML pages are in _build/html.

The HTML rendering of the docs ends up in :file:`docs/_build/html/`.
You can open the :file:`index.html` file in that directory tree in your browser to preview the results of the build.

If you have write access to the `repository`_ on GitHub,
whenever you push changes to GitHub the documentation is automatically re-built and rendered at https://salishsea-nowcast.readthedocs.io/en/latest/.


.. _SalishSeaNowcastLinkCheckingTheDocumentation:

Link Checking the Documentation
-------------------------------

.. image:: https://github.com/SalishSeaCast/SalishSeaNowcast/actions/workflows/sphinx-linkcheck.yaml/badge.svg
      :target: https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:sphinx-linkcheck
      :alt: Sphinx linkcheck


Sphinx also provides a link checker utility which can be run to find broken or redirected links in the docs.
With your ``salishsea-nowcast`` environment activated,
use:

.. code-block:: bash

    (salishsea-nowcast)$ cd SalishSeaNowcast/docs/
    (salishsea-nowcast) docs$ make linkcheck

The output looks something like:

.. code-block:: text

    Removing everything under '_build'...
    Running Sphinx v8.1.3
    loading translations [en]... done
    making output directory... done
    loading intersphinx inventory 'python' from https://docs.python.org/3/objects.inv ...
    loading intersphinx inventory 'nemonowcast' from https://nemo-nowcast.readthedocs.io/en/latest/objects.inv ...
    loading intersphinx inventory 'salishseadocs' from https://salishsea-meopar-docs.readthedocs.io/en/latest/objects.inv ...
    loading intersphinx inventory 'salishseatools' from https://salishsea-meopar-tools.readthedocs.io/en/latest/objects.inv ...
    loading intersphinx inventory 'salishseasite' from https://salishsea-site.readthedocs.io/objects.inv ...
    loading intersphinx inventory 'salishseacmd' from https://salishseacmd.readthedocs.io/en/latest/objects.inv ...
    building [mo]: targets for 0 po files that are out of date
    writing output...
    building [linkcheck]: targets for 20 source files that are out of date
    updating environment: [new config] 20 added, 0 changed, 0 removed
    reading sources... [100%] workers
    looking for now-outdated files... none found
    pickling environment... done
    checking consistency... done
    preparing documents... done
    copying assets...
    copying assets: done
    writing output... [100%] workers

    (deployment/arbutus_cloud: line  679) -ignored- https://polar.ncep.noaa.gov/waves/wavewatch/distribution/
    (deployment/arbutus_cloud: line  764) -ignored- https://gitlab.com/mdunphy/FVCOM41
    (figures/fig_dev_env: line   59) -ignored- https://github.com/SalishSeaCast/tidal-predictions
    (deployment/operations: line   35) ok        http://supervisord.org/
    (deployment/operations: line   68) ok        http://supervisord.org/running.html#running-supervisorctl
    (deployment/arbutus_cloud: line   34) redirect  https://arbutus.cloud.computecanada.ca/ - with Found to https://arbutus.cloud.computecanada.ca/auth/login/?next=/
    (deployment/arbutus_cloud: line   39) ok        https://ccdb.alliancecan.ca/security/login
    (           index: line   60) ok        https://alliancecan.ca/en
    ( pkg_development: line   23) ok        https://app.codecov.io/gh/SalishSeaCast/SalishSeaNowcast
    (figures/create_fig_module: line  870) ok        https://black.readthedocs.io/en/stable/
    (           index: line   60) ok        https://arc.ubc.ca/
    (deployment/arbutus_cloud: line   49) ok        https://docs.alliancecan.ca/wiki/Cloud_Quick_Start
    ( pkg_development: line  637) ok        https://coverage.readthedocs.io/en/latest/
    (figures/website_theme: line   41) ok        https://bootswatch.com/superhero/
    ( pkg_development: line   29) ok        https://codecov.io/gh/SalishSeaCast/SalishSeaNowcast/branch/main/graph/badge.svg
    (figures/fig_dev_env: line   25) ok        https://docs.conda.io/en/latest/
    (deployment/arbutus_cloud: line  781) ok        https://docs.conda.io/en/latest/miniconda.html
    (deployment/operations: line   35) ok        https://dd.weather.gc.ca/
    ( pkg_development: line  679) ok        https://docs.github.com/en/actions
    (deployment/arbutus_cloud: line   25) ok        https://docs.alliancecan.ca/wiki/Cloud_resources#Arbutus_cloud
    (deployment/skookum: line  415) redirect  https://ccdb.computecanada.ca/ssh_authorized_keys - with Found to https://ccdb.alliancecan.ca/security/login
    (deployment/arbutus_cloud: line   49) ok        https://docs.openstack.org/queens/user/
    ( pkg_development: line  545) ok        https://docs.pytest.org/en/latest/
    (deployment/arbutus_cloud: line   34) ok        https://docs.openstack.org/horizon/stein/user/
    ( pkg_development: line   23) ok        https://docs.python.org/3.12/
    (         workers: line  594) ok        https://docs.python.org/3/library/constants.html#True
    (         workers: line  446) ok        https://docs.python.org/3/library/constants.html#None
    (         workers: line   32) ok        https://docs.python.org/3/library/exceptions.html#ValueError
    (         workers: line  446) ok        https://docs.python.org/3/library/datetime.html#datetime.datetime
    (         workers: line    3) ok        https://docs.python.org/3/library/logging.handlers.html#logging.handlers.RotatingFileHandler
    (         workers: line  446) ok        https://docs.python.org/3/library/functions.html#float
    (         workers: line    3) ok        https://docs.python.org/3/library/logging.handlers.html#logging.handlers.RotatingFileHandler.doRollover
    (         workers: line  404) ok        https://docs.python.org/3/library/functions.html#int
    (         workers: line  404) ok        https://docs.python.org/3/library/logging.html#logging.Logger
    (         workers: line  404) ok        https://docs.python.org/3/library/pathlib.html#pathlib.Path
    (         workers: line  404) ok        https://docs.python.org/3/library/stdtypes.html#list
    (         workers: line  404) ok        https://docs.python.org/3/library/stdtypes.html#str
    (figures/make_figure_calls: line  120) ok        https://docs.python.org/3/library/stdtypes.html#dict
    (figures/create_fig_module: line  673) ok        https://docs.python.org/3/library/types.html#types.SimpleNamespace
    (figures/make_figure_calls: line  148) ok        https://docs.python.org/3/library/stdtypes.html#tuple
    (figures/fig_dev_env: line   37) ok        https://docs.python.org/3/whatsnew/3.6.html#whatsnew36-pep519
    (figures/fig_dev_env: line   35) ok        https://docs.python.org/3/reference/lexical_analysis.html#f-strings
    (           index: line   25) ok        https://eccc-msc.github.io/open-data/msc-data/nwp_hrdps/readme_hrdps_en/
    (deployment/index: line   35) ok        https://en.wikipedia.org/wiki/Ceph_(software)
    ( pkg_development: line  693) ok        https://git-scm.com/
    (figures/fig_dev_env: line   53) ok        https://github.com/43ravens/NEMO_Nowcast
    (deployment/operations: line   35) ok        https://github.com/MetPX/sarracenia/blob/v2_dev/doc/sr_subscribe.1.rst
    (figures/fig_dev_env: line   56) ok        https://github.com/SalishSeaCast/NEMO-Cmd
    (         workers: line    1) ok        https://climate.weather.gc.ca/
    ( pkg_development: line  132) ok        https://github.com/SalishSeaCast/FVCOM-Cmd
    ( pkg_development: line   26) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/actions/workflows/pytest-with-coverage.yaml/badge.svg
    (figures/fig_dev_env: line   58) ok        https://github.com/SalishSeaCast/SalishSeaNowcast
    (figures/fig_dev_env: line   57) ok        https://github.com/SalishSeaCast/SalishSeaCmd
    ( pkg_development: line   32) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/actions/workflows/codeql-analysis.yaml/badge.svg
    ( pkg_development: line  668) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/actions
    ( pkg_development: line   39) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/actions/workflows/sphinx-linkcheck.yaml/badge.svg
    ( pkg_development: line  668) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/commits/main
    ( pkg_development: line   23) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/issues
    ( pkg_development: line   23) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:CodeQL
    (           index: line  115) ok        https://github.com/SalishSeaCast/docs/blob/main/CONTRIBUTORS.rst
    ( pkg_development: line   23) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:sphinx-linkcheck
    ( pkg_development: line   23) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:pytest-with-coverage
    (deployment/skookum: line   99) ok        https://github.com/SalishSeaCast/salishsea-site
    ( pkg_development: line   23) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/releases
    (figures/fig_dev_env: line   55) ok        https://github.com/SalishSeaCast/tools
    (figures/fig_dev_env: line   54) ok        https://github.com/UBC-MOAD/moad_tools
    (deployment/skookum: line   58) ok        https://github.com/conda-forge/miniforge
    ( pkg_development: line   23) ok        https://github.com/pypa/hatch
    ( pkg_development: line   65) ok        https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg
    ( pkg_development: line   53) ok        https://img.shields.io/badge/license-Apache%202-cb2533.svg
    ( pkg_development: line   59) ok        https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
    ( pkg_development: line   62) ok        https://img.shields.io/badge/code%20style-black-000000.svg
    ( pkg_development: line   56) ok        https://img.shields.io/badge/version%20control-git-blue.svg?logo=github
    ( pkg_development: line   49) ok        https://img.shields.io/github/issues/SalishSeaCast/SalishSeaNowcast?logo=github
    ( pkg_development: line   43) ok        https://img.shields.io/github/v/release/SalishSeaCast/SalishSeaNowcast?logo=github
    ( pkg_development: line   46) ok        https://img.shields.io/python/required-version-toml?tomlFilePath=https://raw.githubusercontent.com/SalishSeaCast/SalishSeaNowcast/main/pyproject.toml&logo=Python&logoColor=gold&label=Python
    ( pkg_development: line  129) ok        https://gitlab.com/mdunphy/OPPTools
    (         workers: line   10) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/comparison/TestSandHeadsWinds.ipynb
    (         workers: line    5) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/comparison/TestSalinityFerryTrackModule.ipynb
    (         workers: line    9) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/fvcom/publish/DevelopTideStnWaterLevel.ipynb
    (         workers: line    5) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/fvcom/publish/TestSecondNarrowsCurrent.ipynb
    (deployment/operations: line  122) ok        https://github.com/SalishSeaCast/salishsea-site/actions?query=workflow:deployment
    (         workers: line    6) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/fvcom/publish/TestTideStnWaterLevel.ipynb
    (         workers: line    4) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/fvcom/research/TestSurfaceCurrents.ipynb
    (         workers: line   23) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/publish/TestCompareTidePredictionMaxSSH.ipynb
    (         workers: line    8) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/fvcom/publish/DevelopSecondNarrowsCurrent.ipynb
    (         workers: line   11) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/publish/TestPtAtkinsonTideModule.ipynb
    (         workers: line   11) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/publish/TestStormSurgeAlertsModule.ipynb
    (         workers: line   13) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/publish/TestStormSurgeAlertsThumbnailModule.ipynb
    (         workers: line   13) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/DevelopTimeSeriesPlots.ipynb
    (figures/create_fig_module: line   36) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/DevelopTracerThalwegAndSurfaceModule.ipynb
    (         workers: line   26) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/publish/DevelopCompareTidePredictionMaxSSH.ipynb
    (figures/create_fig_module: line   42) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/TestTracerThalwegAndSurface.ipynb
    (         workers: line   10) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/TestTimeSeriesPlots.ipynb
    (         workers: line    9) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/wwatch3/DevelopWaveHeightPeriod.ipynb
    (         workers: line    6) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/wwatch3/TestWaveHeightPeriod.ipynb
    (         workers: line   12) ok        https://nbviewer.org/github/SalishSeaCast/analysis-doug/blob/main/notebooks/ONC-CTD-DataToERDDAP.ipynb
    (creating_workers: line   25) ok        https://nemo-nowcast.readthedocs.io/en/latest/
    (deployment/index: line   30) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#module-nemo_nowcast.manager
    (deployment/index: line   30) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#module-nemo_nowcast.log_aggregator
    ( pkg_development: line  130) ok        https://nemo-cmd.readthedocs.io/en/latest/
    (deployment/index: line   30) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#module-nemo_nowcast.message_broker
    (         workers: line  428) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#nemo_nowcast.config.Config
    (deployment/arbutus_cloud: line  428) ok        https://help.ubuntu.com/community/SettingUpNFSHowTo
    (           index: line   69) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#nemo-nowcastbuiltinworkers
    (         workers: line  428) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#nemo_nowcast.message.Message
    (           index: line   69) ok        https://nemo-nowcast.readthedocs.io/en/latest/architecture/index.html#frameworkarchitecture
    (         workers: line   41) ok        https://nemo-nowcast.readthedocs.io/en/latest/architecture/message_broker.html#messagebroker
    (         workers: line   37) ok        https://nemo-nowcast.readthedocs.io/en/latest/architecture/manager.html#systemmanager
    (         workers: line   37) ok        https://nemo-nowcast.readthedocs.io/en/latest/architecture/messaging.html#messagingsystem
    (creating_workers: line   25) ok        https://nemo-nowcast.readthedocs.io/en/latest/nowcast_system/workers.html#creatingnowcastworkermodules
    ( worker_failures: line   28) ok        https://nomads.ncep.noaa.gov/pub/data/nccf/com/petss/prod/
    (figures/create_fig_module: line  870) ok        https://peps.python.org/pep-0008/
    ( pkg_development: line  637) ok        https://pytest-cov.readthedocs.io/en/latest/
    (deployment/arbutus_cloud: line  693) ok        https://polar.ncep.noaa.gov/waves/wavewatch/manual.v5.16.pdf
    (deployment/arbutus_cloud: line  679) ok        https://polar.ncep.noaa.gov/waves/wavewatch/license.shtml
    ( pkg_development: line   23) ok        https://pre-commit.com
    (deployment/index: line   25) ok        https://salishsea-meopar-docs.readthedocs.io/en/latest/repos_organization.html#salishseanowcast-repo
    ( pkg_development: line  200) ok        https://pre-commit.com/
    ( pkg_development: line  127) ok        https://reshapr.readthedocs.io/en/latest/index.html
    (deployment/index: line   30) ok        https://salishsea-meopar-docs.readthedocs.io/en/latest/results_server/index.html#salishseamodelresultsserver
    (figures/create_fig_module: line   25) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaNowcast/index.html#salishseanowcastpackage
    ( pkg_development: line   36) ok        https://readthedocs.org/projects/salishsea-nowcast/badge/?version=latest
    (figures/create_fig_module: line  678) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#module-salishsea_tools.places
    (         workers: line    4) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#salishsea_tools.stormtools.correct_model
    (         workers: line  478) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#salishsea_tools.places.PLACES
    (         workers: line  446) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#salishsea_tools.stormtools.storm_surge_risk_level
    (figures/create_fig_module: line  764) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#salishsea_tools.visualisations.contour_thalweg
    (figures/create_fig_module: line  365) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodeautogenerateddocs
    (figures/create_fig_module: line  395) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/index.html#salishseatoolspackage
    (figures/fig_modules: line   62) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#salishsea_tools.viz_tools.set_aspect
    (figures/create_fig_module: line  413) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodeimports
    (figures/create_fig_module: line  673) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodereturnsimplenamespacesfromfunctions
    (figures/create_fig_module: line  423) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodepublicandprivate
    (figures/create_fig_module: line  340) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodestandardcopyrightheaderblock
    (figures/create_fig_module: line  678) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodesalishseatoolsplaces
    ( pkg_development: line   23) ok        https://salishsea-nowcast.readthedocs.io/en/latest/
    (figures/site_view_fig_metadata: line   45) ok        https://salishsea-site.readthedocs.io
    (         workers: line    7) ok        https://salishsea-nowcast.readthedocs.io/en/latest/figures/create_fig_module.html#creating-a-figure-module
    (   figures/index: line   36) ok        https://salishsea-site.readthedocs.io/
    (deployment/operations: line   56) ok        https://salishsea.eos.ubc.ca
    (           index: line   25) ok        https://salishsea.eos.ubc.ca/nemo/
    (deployment/skookum: line   99) ok        https://salishsea.eos.ubc.ca/
    (         workers: line  602) ok        https://salishsea.eos.ubc.ca/erddap/griddap/index.html?page=1&itemsPerPage=1000
    ( worker_failures: line   52) ok        https://salishsea.eos.ubc.ca/nemo/nowcast/logs/nowcast.debug.log
    (           index: line   55) ok        https://salishsea.eos.ubc.ca/erddap/index.html
    (         workers: line    9) ok        https://salishsea.eos.ubc.ca/erddap/tabledap/index.html?page=1&itemsPerPage=1000
    ( worker_failures: line   52) ok        https://salishsea.eos.ubc.ca/nemo/nowcast/logs/nowcast.log
    (         workers: line    8) ok        https://salishsea.eos.ubc.ca/storm-surge/
    (   figures/index: line   23) ok        https://salishsea.eos.ubc.ca/nemo/results/
    ( pkg_development: line  131) ok        https://salishseacmd.readthedocs.io/en/latest/index.html#salishseacmdprocessor
    ( pkg_development: line  126) ok        https://ubc-moad-tools.readthedocs.io/en/latest/index.html
    (           index: line  120) ok        https://www.apache.org/licenses/LICENSE-2.0
    (deployment/arbutus_cloud: line   25) ok        https://www.oceannetworks.ca/
    (         workers: line   12) redirect  https://www.eoas.ubc.ca/~rich/#T_Tide - temporarily to https://www-old.eoas.ubc.ca/~rich/
    (deployment/index: line   98) ok        https://salishseacast.slack.com/?redir=%2Farchives%2FC011S7BCWGK
    ( worker_failures: line   28) ok        https://tidesandcurrents.noaa.gov/waterlevels.html?id=9443090
    ( pkg_development: line   86) ok        https://www.python.org/
    ( pkg_development: line  233) ok        https://www.sphinx-doc.org/en/master/
    (deployment/arbutus_cloud: line   25) ok        https://www.openstack.org/
    ( pkg_development: line  233) ok        https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
    (figures/create_fig_module: line  546) ok        https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html#info-field-lists
    (         workers: line    1) ok        https://www.ndbc.noaa.gov/data/realtime2/
    build succeeded.

    Look for any errors in the above output or in _build/linkcheck/output.txt

:command:`make linkcheck` is run monthly via a `scheduled GitHub Actions workflow`_

.. _scheduled GitHub Actions workflow: https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:sphinx-linkcheck


.. _SalishSeaNowcastRunningTheUnitTests:

Running the Unit Tests
======================

The test suite for the ``SalishSeaNowcast`` package is in :file:`SalishSeaNowcast/tests/`.
The `pytest`_ tool is used for test parametrization and as the test runner for the suite.

.. _pytest: https://docs.pytest.org/en/latest/

With your ``salishsea-nowcast`` development environment activated,
use:

.. code-block:: bash

    (salishsea-nowcast)$ cd SalishSeaNowcast/
    (salishsea-nowcast)$ pytest

to run the test suite.
The output looks something like:

.. code-block:: text

    ================================ test session starts ================================
    platform linux -- Python 3.13.1, pytest-8.3.4, pluggy-1.5.0
    Using --randomly-seed=4145810385
    rootdir: /media/doug/warehouse/MEOPAR/SalishSeaNowcast
    configfile: pyproject.toml
    plugins: anyio-4.8.0, randomly-3.15.0, httpx-0.35.0, cov-6.0.0, xdist-3.6.1
    collected 2372 items

    tests/workers/test_make_live_ocean_files.py .........                          [  0%]
    tests/workers/test_run_ww3.py .......................................................
    ..............                                                                 [  3%]
    tests/test_next_workers.py ..........................................................
    .....................................................................................
    .....................................................................................
    .....................................................................................
    ..................................................................             [ 19%]
    tests/workers/test_watch_NEMO.py ....................................................
    ............................                                                   [ 22%]
    tests/workers/test_collect_weather.py ...............................................
    ......                                                                         [ 24%]
    tests/workers/test_run_NEMO_agrif.py .................                         [ 25%]
    tests/workers/test_make_plots.py ....................................................
    .............................................                                  [ 29%]
    tests/workers/test_upload_fvcom_atmos_forcing.py ............................  [ 30%]
    tests/workers/test_make_feeds.py .....................                         [ 31%]
    tests/workers/test_get_onc_ferry.py ................................           [ 33%]
    tests/workers/test_watch_ww3.py ..................                             [ 33%]
    tests/workers/test_make_fvcom_rivers_forcing.py ..............................
    ....                                                                           [ 35%]
    tests/test_daily_river_flows.py ......................................         [ 36%]
    tests/workers/make_runoff_file.py ...................................................
    ...........                                                                    [ 39%]
    tests/workers/test_collect_NeahBay_ssh.py ...................                  [ 40%]
    tests/workers/test_make_fvcom_atmos_forcing.py ...............................
    ....                                                                           [ 41%]
    tests/workers/test_download_fvcom_results.py ...........................       [ 42%]
    tests/workers/test_upload_forcing.py .........................................
    ...............................                                                [ 45%]
    tests/workers/test_launch_remote_worker.py ...............                     [ 46%]
    tests/test_analyze.py .................                                        [ 47%]
    tests/workers/test_watch_fvcom.py .............................                [ 48%]
    tests/workers/test_watch_NEMO_agrif.py ....................                    [ 49%]
    tests/workers/test_make_surface_current_tiles.py ...........................   [ 50%]
    tests/workers/test_make_averaged_dataset.py ..................................
    ........                                                                       [ 52%]
    tests/workers/test_make_ssh_file.py .................                          [ 52%]
    tests/workers/test_get_onc_ctd.py ............                                 [ 53%]
    tests/workers/test_split_results.py .............                              [ 54%]
    tests/workers/test_run_NEMO_hindcast.py .............................................
    .....................................................................................
    ..............                                                                 [ 60%]
    tests/workers/test_rotate_hindcast_logs.py ..........                          [ 60%]
    tests/workers/test_make_forcing_links.py ............................................
    ..................                                                             [ 64%]
    tests/workers/test_ping_erddap.py ..........................................   [ 66%]
    tests/workers/test_get_vfpa_hadcp.py ..............                            [ 66%]
    tests/workers/test_grib_to_netcdf.py ................................................
    .............                                                                  [ 69%]
    tests/workers/test_download_live_ocean.py .........                            [ 69%]
    tests/test_residuals.py ...                                                    [ 70%]
    tests/workers/test_make_turbidity_file.py ......                               [ 70%]
    tests/workers/test_make_ww3_current_file.py .................................  [ 71%]
    tests/release_mgmt/test_tag_release.py .........                               [ 72%]
    tests/workers/test_download_results.py ..............................................
    .........................                                                      [ 75%]
    tests/workers/test_watch_NEMO_hindcast.py ...........................................
    ....................                                                           [ 77%]
    tests/workers/test_make_201702_runoff_file.py ............                     [ 78%]
    tests/workers/test_crop_gribs.py ..............................................[ 80%]
    tests/test_config.py ..............................                            [ 81%]
    tests/workers/test_download_weather.py ..............................................
    ......                                                                         [ 83%]
    tests/workers/test_archive_tarball.py ........................                 [ 84%]
    tests/workers/test_make_ww3_wind_file.py ..........................            [ 85%]
    tests/workers/test_collect_river_data.py ...........................           [ 86%]
    tests/workers/test_run_NEMO.py ......................................................
    .............................................................................. [ 92%]
    tests/workers/test_make_CHS_currents_file.py ........................          [ 93%]
    tests/workers/test_run_fvcom.py .....................................................
    .............                                                                  [ 96%]
    tests/workers/test_update_forecast_datasets.py ......................................
    .....................................                                          [ 99%]
    tests/workers/test_download_wwatch3_results.py ............                    [100%]

    =============================== 2372 passed in 41.82s ================================

You can monitor what lines of code the test suite exercises using the `coverage.py`_ and `pytest-cov`_ tools with the command:

.. _coverage.py: https://coverage.readthedocs.io/en/latest/
.. _pytest-cov: https://pytest-cov.readthedocs.io/en/latest/

.. code-block:: bash

    (salishsea-nowcast)$ cd SalishSeaNowcast/
    (salishsea-nowcast)$ pytest --cov=./

The test coverage report will be displayed below the test suite run output.

Alternatively,
you can use

.. code-block:: bash

    (salishsea-nowcast)$ pytest --cov=./ --cov-report html

to produce an HTML report that you can view in your browser by opening :file:`SalishSeaNowcast/htmlcov/index.html`.


.. _SalishSeaNowcastContinuousIntegration:

Continuous Integration
----------------------

.. image:: https://github.com/SalishSeaCast/SalishSeaNowcast/actions/workflows/pytest-with-coverage.yaml/badge.svg
    :target: https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:pytest-with-coverage
    :alt: GitHub Workflow Status

The ``SalishSeaNowcast`` package unit test suite is run and a coverage report is generated whenever changes are pushed to GitHub.
The results are visible on the `repo actions page`_,
from the green checkmarks beside commits on the `repo commits page`_,
or from the green checkmark to the left of the "Latest commit" message on the `repo code overview page`_ .
The testing coverage report is uploaded to `codecov.io`_

.. _repo actions page: https://github.com/SalishSeaCast/SalishSeaNowcast/actions
.. _repo commits page: https://github.com/SalishSeaCast/SalishSeaNowcast/commits/main
.. _repo code overview page: https://github.com/SalishSeaCast/SalishSeaNowcast
.. _codecov.io: https://app.codecov.io/gh/SalishSeaCast/SalishSeaNowcast

The `GitHub Actions`_ workflow configuration that defines the continuous integration tasks is in the :file:`.github/workflows/pytest-coverage.yaml` file.

.. _GitHub Actions: https://docs.github.com/en/actions


.. _SalishSeaNowcastVersionControlRepository:

Version Control Repository
==========================

.. image:: https://img.shields.io/badge/version%20control-git-blue.svg?logo=github
    :target: https://github.com/SalishSeaCast/SalishSeaNowcast
    :alt: Git on GitHub

The ``SalishSeaNowcast`` package code and documentation source files are available as a `Git`_ repository at https://github.com/SalishSeaCast/SalishSeaNowcast.

.. _Git: https://git-scm.com/


.. _SalishSeaNowcastIssueTracker:

Issue Tracker
=============

.. image:: https://img.shields.io/github/issues/SalishSeaCast/SalishSeaNowcast?logo=github
    :target: https://github.com/SalishSeaCast/SalishSeaNowcast/issues
    :alt: Issue Tracker

Development tasks,
bug reports,
and enhancement ideas are recorded and managed in the issue tracker at https://github.com/SalishSeaCast/SalishSeaNowcast/issues.


License
=======

.. image:: https://img.shields.io/badge/license-Apache%202-cb2533.svg
    :target: https://www.apache.org/licenses/LICENSE-2.0
    :alt: Licensed under the Apache License, Version 2.0

The SalishSeaCast NEMO model nowcast system code and documentation are copyright 2013 – present
by the `SalishSeaCast Project Contributors`_ and The University of British Columbia.

.. _SalishSeaCast Project Contributors: https://github.com/SalishSeaCast/docs/blob/main/CONTRIBUTORS.rst

They are licensed under the Apache License, Version 2.0.
https://www.apache.org/licenses/LICENSE-2.0
Please see the LICENSE file for details of the license.


Release Process
===============

.. image:: https://img.shields.io/github/v/release/SalishSeaCast/SalishSeaNowcast?logo=github
    :target: https://github.com/SalishSeaCast/SalishSeaNowcast/releases
    :alt: Releases
.. image:: https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg
    :target: https://github.com/pypa/hatch
    :alt: Hatch project

Releases are done at Doug's discretion when significant pieces of development work have been
completed.

The release process steps are:

#. Use :command:`hatch version release` to bump the version from ``.devn`` to the next release
   version identifier

#. Commit the version bump

#. Create an annotated tag for the release with :guilabel:`Git -> New Tag...` in PyCharm
   or :command:`git tag -e -a vyy.n`

#. Push the version bump commit and tag to GitHub

#. Use the GitHub web interface to create a release,
   editing the auto-generated release notes into sections:

   * Features
   * Bug Fixes
   * Documentation
   * Maintenance
   * Dependency Updates

#. Use the GitHub :guilabel:`Issues -> Milestones` web interface to edit the release
   milestone:

   * Change the :guilabel:`Due date` to the release date
   * Delete the "when it's ready" comment in the :guilabel:`Description`

#. Use the GitHub :guilabel:`Issues -> Milestones` web interface to create a milestone for
   the next release:

   * Set the :guilabel:`Title` to the next release version,
     prepended with a ``v``;
     e.g. ``v23.1``
   * Set the :guilabel:`Due date` to the end of the year of the next release
   * Set the :guilabel:`Description` to something like
     ``v23.1 release - when it's ready :-)``
   * Create the next release milestone

#. Review the open issues,
   especially any that are associated with the milestone for the just released version,
   and update their milestone.

#. Close the milestone for the just released version.

#. Use :command:`hatch version minor,dev` to bump the version for the next development cycle,
   or use :command:`hatch version major,minor,dev` for a year rollover version bump

#. Commit the version bump

#. Push the version bump commit to GitHub
