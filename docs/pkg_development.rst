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
| **Documentation**          | .. image:: https://app.readthedocs.org/projects/salishsea-nowcast/badge/?version=latest                                                                                                                  |
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

.. code-block:: console

    $ git clone git@github.com:SalishSeaCast/SalishSeaNowcast.git


.. _SalishSeaNowcastDevelopmentEnvironment:

Development Environment
=======================

:py:obj:`SalishSeaNowcast` uses Pixi_ for package and environment management.
If you don't already have Pixi_ installed,
please follow its `installation instructions`_ to do so.

.. _Pixi: https://pixi.prefix.dev/latest/
.. _`installation instructions`: https://pixi.prefix.dev/latest/installation/

Use :command:`pixi install` command to download the package dependencies and link them into environments.

Most commands are executed using :command:`pixi run` in the :file:`SalishSeaNowcast/` directory
(or a sub-directory).

* The ``default`` environment has the packages installed that are required to run the
  :py:obj:`Reshapr` command-line interface;
  e.g. :command:`pixi run reshapr help`

* Other environments used by commands in the sections below have addition packages for running
  the test suite,
  building and link checking the documentation,
  etc.

* If you are using an integrated development environment like VSCode or PyCharm
  where you need a Python interpreter to support coding assistance features,
  run development tasks,
  etc.,
  use the interpreter in the ``dev`` environment.
  You can get its full path with :command:`pixi run -e dev which python`

You can launch a sub-shell in one of the environments with a command like :command:`pixi shell -e dev`.
That is convenient if you are running a lot of commands because it removed the need to type
:command:`pixi run -e dev` before each of them.
Use :command:`exit` to leave the sub-shell.

:py:obj:`SalishSeaNowcast` depends on a collection of other Python packages developed by the SalishSeaCast project and friends:

* `NEMO_Nowcast`_
* `moad_tools`_
* `Reshapr`_
* :ref:`SalishSeaToolsPackage`
* `NEMO-Cmd`_
* :ref:`SalishSeaCmdProcessor`

.. _moad_tools: https://ubc-moad-tools.readthedocs.io/en/latest/index.html
.. _Reshapr: https://reshapr.readthedocs.io/en/latest/index.html
.. _NEMO-Cmd: https://nemo-cmd.readthedocs.io/en/latest/

Those packages are installed by the :command:`pixi install` command.

To get detailed information about the environments,
the packages installed in them,
`Pixi`_ tasks that are defined for them,
etc.,
use :command:`pixi info`.

:py:obj:`SalishSeaNowcast` is installed in `editable install mode`_ in all of the environments that
`Pixi`_ creates.
That means that changes you make to the code are immediately reflected in the environments.

.. _editable install mode: https://pip.pypa.io/en/stable/topics/local-project-installs/#editable-installs


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
run :command:`pre-commit install`:

.. code-block:: console

    $ cd SalishSeaNowcast
    $ pixi run -e dev pre-commit install

.. note::
    You only need to install the hooks once immediately after you make a new clone of the
    `SalishSeaNowcast repository`_ and build your :ref:`SalishSeaNowcastDevelopmentEnvironment`.

.. _SalishSeaNowcast repository: https://github.com/SalishSeaCast/SalishSeaNowcast


.. _SalishSeaNowcastBuildingTheDocumentation:

Building the Documentation
==========================

.. image:: https://app.readthedocs.org/projects/salishsea-nowcast/badge/?version=latest
    :target: https://salishsea-nowcast.readthedocs.io/en/latest/
    :alt: Documentation Status

The documentation for the ``SalishSeaNowcast`` package is written in `reStructuredText`_ and converted to HTML using `Sphinx`_.
Creating a :ref:`SalishSeaNowcastDevelopmentEnvironment` as described above includes the installation of Sphinx.
Building the documentation is driven by the :file:`docs/Makefile`.
To do a clean build of the documentation use:

.. _reStructuredText: https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
.. _Sphinx: https://www.sphinx-doc.org/en/master/

.. code-block:: console

    $ cd SalishSeaNowcast
    $ pixi run docs

The output looks something like:

.. code-block:: text
   :class: no-copybutton

    ✨ Pixi task (docs in docs): make clean html
    Removing everything under '_build'...
    Running Sphinx v9.1.0
    loading translations [en]... done
    making output directory... done
    loading intersphinx inventory 'python' from https://docs.python.org/3/objects.inv ...
    loading intersphinx inventory 'nemonowcast' from https://nemo-nowcast.readthedocs.io/en/latest/objects.inv ...
    loading intersphinx inventory 'salishseatools' from https://salishsea-meopar-tools.readthedocs.io/en/latest/objects.inv ...
    loading intersphinx inventory 'salishseasite' from https://salishsea-site.readthedocs.io/objects.inv ...
    loading intersphinx inventory 'salishseadocs' from https://salishsea-meopar-docs.readthedocs.io/en/latest/objects.inv ...
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
    Writing evaluated template result to /media/doug/warehouse/MEOPAR/SalishSeaNowcast/docs/_build/html/_static/documentation_options.js
    Writing evaluated template result to /media/doug/warehouse/MEOPAR/SalishSeaNowcast/docs/_build/html/_static/basic.css
    Writing evaluated template result to /media/doug/warehouse/MEOPAR/SalishSeaNowcast/docs/_build/html/_static/js/versions.js
    Writing evaluated template result to /media/doug/warehouse/MEOPAR/SalishSeaNowcast/docs/_build/html/_static/copybutton.js
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
Run the link checker with:

.. code-block:: console

    $ cd SalishSeaNowcast
    $ pixi run linkcheck

The output looks something like:

.. code-block:: text
   :class: no-copybutton

    ✨ Pixi task (linkcheck in docs): make clean linkcheck
    Removing everything under '_build'...
    Running Sphinx v9.1.0
    loading translations [en]... done
    making output directory... done
    loading intersphinx inventory 'python' from https://docs.python.org/3/objects.inv ...
    loading intersphinx inventory 'nemonowcast' from https://nemo-nowcast.readthedocs.io/en/latest/objects.inv ...
    loading intersphinx inventory 'salishseadocs' from https://salishsea-meopar-docs.readthedocs.io/en/latest/objects.inv ...
    loading intersphinx inventory 'salishseacmd' from https://salishseacmd.readthedocs.io/en/latest/objects.inv ...
    loading intersphinx inventory 'salishseasite' from https://salishsea-site.readthedocs.io/objects.inv ...
    loading intersphinx inventory 'salishseatools' from https://salishsea-meopar-tools.readthedocs.io/en/latest/objects.inv ...
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

    (deployment/arbutus_cloud: line  682) -ignored- https://polar.ncep.noaa.gov/waves/wavewatch/distribution/
    (figures/fig_dev_env: line   59) -ignored- https://github.com/SalishSeaCast/tidal-predictions
    (deployment/arbutus_cloud: line   34) redirect  https://arbutus.cloud.computecanada.ca/ - with Found to https://arbutus.cloud.computecanada.ca/auth/login/?next=/
    (           index: line   60) ok        https://arc.ubc.ca/
    ( pkg_development: line   36) ok        https://app.readthedocs.org/projects/salishsea-nowcast/badge/?version=latest
    ( pkg_development: line   23) ok        https://app.codecov.io/gh/SalishSeaCast/SalishSeaNowcast
    (figures/create_fig_module: line  870) ok        https://black.readthedocs.io/en/stable/
    (figures/website_theme: line   41) ok        https://bootswatch.com/superhero/
    (           index: line   60) redirect  https://alliancecan.ca/en - temporarily to https://www.alliancecan.ca/en
    (deployment/arbutus_cloud: line   39) ok        https://ccdb.alliancecan.ca/security/login
    (         workers: line    1) ok        https://climate.weather.gc.ca/
    ( pkg_development: line  598) ok        https://coverage.readthedocs.io/en/latest/
    ( pkg_development: line   29) ok        https://codecov.io/gh/SalishSeaCast/SalishSeaNowcast/branch/main/graph/badge.svg
    (figures/fig_dev_env: line   25) ok        https://docs.conda.io/en/latest/
    (figures/fig_dev_env: line   47) ok        https://docs.conda.io/en/latest/miniconda.html
    (deployment/operations: line   35) ok        https://dd.weather.gc.ca/
    (deployment/arbutus_cloud: line   49) ok        https://docs.alliancecan.ca/wiki/Cloud_Quick_Start
    (deployment/arbutus_cloud: line   25) ok        https://docs.alliancecan.ca/wiki/Cloud_resources
    ( pkg_development: line  640) ok        https://docs.github.com/en/actions
    ( pkg_development: line   23) ok        https://docs.python.org/3/
    (         workers: line  398) ok        https://docs.python.org/3/library/constants.html#None
    ( pkg_development: line  504) ok        https://docs.pytest.org/en/latest/
    (         workers: line  505) ok        https://docs.python.org/3/library/constants.html#True
    (deployment/skookum: line  413) redirect  https://ccdb.computecanada.ca/ssh_authorized_keys - with Found to https://ccdb.alliancecan.ca/security/login
    (         workers: line  398) ok        https://docs.python.org/3/library/datetime.html#datetime.datetime
    (deployment/arbutus_cloud: line   49) ok        https://docs.openstack.org/queens/user/
    (deployment/arbutus_cloud: line   34) ok        https://docs.openstack.org/horizon/stein/user/
    (         workers: line   32) ok        https://docs.python.org/3/library/exceptions.html#ValueError
    (         workers: line  398) ok        https://docs.python.org/3/library/functions.html#float
    (         workers: line  356) ok        https://docs.python.org/3/library/functions.html#int
    (         workers: line    3) ok        https://docs.python.org/3/library/logging.handlers.html#logging.handlers.RotatingFileHandler
    (         workers: line    3) ok        https://docs.python.org/3/library/logging.handlers.html#logging.handlers.RotatingFileHandler.doRollover
    (figures/make_figure_calls: line  120) ok        https://docs.python.org/3/library/stdtypes.html#dict
    (         workers: line  356) ok        https://docs.python.org/3/library/logging.html#logging.Logger
    (         workers: line  356) ok        https://docs.python.org/3/library/pathlib.html#pathlib.Path
    (figures/make_figure_calls: line  148) ok        https://docs.python.org/3/library/stdtypes.html#tuple
    (         workers: line  356) ok        https://docs.python.org/3/library/stdtypes.html#str
    (         workers: line  356) ok        https://docs.python.org/3/library/stdtypes.html#list
    (figures/create_fig_module: line  673) ok        https://docs.python.org/3/library/types.html#types.SimpleNamespace
    (figures/fig_dev_env: line   35) ok        https://docs.python.org/3/reference/lexical_analysis.html#f-strings
    (figures/fig_dev_env: line   37) ok        https://docs.python.org/3/whatsnew/3.6.html#whatsnew36-pep519
    (           index: line   25) ok        https://eccc-msc.github.io/open-data/msc-data/nwp_hrdps/readme_hrdps_en/
    ( pkg_development: line  654) ok        https://git-scm.com/
    (deployment/index: line   35) ok        https://en.wikipedia.org/wiki/Ceph_(software)
    (figures/fig_dev_env: line   53) ok        https://github.com/43ravens/NEMO_Nowcast
    (figures/fig_dev_env: line   56) ok        https://github.com/SalishSeaCast/NEMO-Cmd
    (figures/fig_dev_env: line   57) ok        https://github.com/SalishSeaCast/SalishSeaCmd
    (figures/fig_dev_env: line   58) ok        https://github.com/SalishSeaCast/SalishSeaNowcast
    ( pkg_development: line   32) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/actions/workflows/codeql-analysis.yaml/badge.svg
    ( pkg_development: line   26) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/actions/workflows/pytest-with-coverage.yaml/badge.svg
    ( pkg_development: line   39) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/actions/workflows/sphinx-linkcheck.yaml/badge.svg
    (deployment/operations: line   35) ok        https://github.com/MetPX/sarracenia/blob/v2_dev/doc/sr_subscribe.1.rst
    ( pkg_development: line  629) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/actions
    ( pkg_development: line   23) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/issues
    ( pkg_development: line   23) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:CodeQL
    ( pkg_development: line  629) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/commits/main
    ( pkg_development: line   23) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:sphinx-linkcheck
    ( pkg_development: line   23) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:pytest-with-coverage
    (           index: line  115) ok        https://github.com/SalishSeaCast/docs/blob/main/CONTRIBUTORS.rst
    ( pkg_development: line   23) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/releases
    (deployment/skookum: line   95) ok        https://github.com/SalishSeaCast/salishsea-site
    (figures/fig_dev_env: line   55) ok        https://github.com/SalishSeaCast/tools
    (figures/fig_dev_env: line   54) ok        https://github.com/UBC-MOAD/moad_tools
    ( pkg_development: line   65) ok        https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg
    ( pkg_development: line   62) ok        https://img.shields.io/badge/code%20style-black-000000.svg
    ( pkg_development: line   53) ok        https://img.shields.io/badge/license-Apache%202-cb2533.svg
    ( pkg_development: line   59) ok        https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
    ( pkg_development: line   56) ok        https://img.shields.io/badge/version%20control-git-blue.svg?logo=github
    (deployment/arbutus_cloud: line  751) ok        https://github.com/conda-forge/miniforge
    ( pkg_development: line   23) ok        https://github.com/pypa/hatch
    ( pkg_development: line   49) ok        https://img.shields.io/github/issues/SalishSeaCast/SalishSeaNowcast?logo=github
    (deployment/arbutus_cloud: line  425) ok        https://help.ubuntu.com/community/SettingUpNFSHowTo
    ( pkg_development: line   46) ok        https://img.shields.io/python/required-version-toml?tomlFilePath=https://raw.githubusercontent.com/SalishSeaCast/SalishSeaNowcast/main/pyproject.toml&logo=Python&logoColor=gold&label=Python
    ( pkg_development: line   43) ok        https://img.shields.io/github/v/release/SalishSeaCast/SalishSeaNowcast?logo=github
    (deployment/operations: line  122) ok        https://github.com/SalishSeaCast/salishsea-site/actions?query=workflow:deployment
    (         workers: line    5) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/comparison/TestSalinityFerryTrackModule.ipynb
    (         workers: line   11) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/publish/TestPtAtkinsonTideModule.ipynb
    (         workers: line   10) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/comparison/TestSandHeadsWinds.ipynb
    (         workers: line   26) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/publish/DevelopCompareTidePredictionMaxSSH.ipynb
    (         workers: line   13) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/publish/TestStormSurgeAlertsThumbnailModule.ipynb
    (         workers: line   23) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/publish/TestCompareTidePredictionMaxSSH.ipynb
    (         workers: line   11) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/publish/TestStormSurgeAlertsModule.ipynb
    (         workers: line   13) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/DevelopTimeSeriesPlots.ipynb
    (figures/create_fig_module: line   36) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/DevelopTracerThalwegAndSurfaceModule.ipynb
    (         workers: line    9) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/wwatch3/DevelopWaveHeightPeriod.ipynb
    (         workers: line   10) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/TestTimeSeriesPlots.ipynb
    ( pkg_development: line  129) ok        https://nemo-cmd.readthedocs.io/en/latest/
    (creating_workers: line   25) ok        https://nemo-nowcast.readthedocs.io/en/latest/
    (         workers: line    6) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/wwatch3/TestWaveHeightPeriod.ipynb
    (figures/create_fig_module: line   42) ok        https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/TestTracerThalwegAndSurface.ipynb
    (deployment/index: line   30) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#module-nemo_nowcast.message_broker
    (deployment/index: line   30) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#module-nemo_nowcast.log_aggregator
    (deployment/index: line   30) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#module-nemo_nowcast.manager
    (           index: line   69) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#nemo-nowcastbuiltinworkers
    (         workers: line  380) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#nemo_nowcast.config.Config
    (         workers: line  380) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#nemo_nowcast.message.Message
    (           index: line   69) ok        https://nemo-nowcast.readthedocs.io/en/latest/architecture/index.html#frameworkarchitecture
    (         workers: line   37) ok        https://nemo-nowcast.readthedocs.io/en/latest/architecture/messaging.html#messagingsystem
    (         workers: line   41) ok        https://nemo-nowcast.readthedocs.io/en/latest/architecture/message_broker.html#messagebroker
    (         workers: line   37) ok        https://nemo-nowcast.readthedocs.io/en/latest/architecture/manager.html#systemmanager
    (figures/create_fig_module: line  870) ok        https://peps.python.org/pep-0008/
    (creating_workers: line   25) ok        https://nemo-nowcast.readthedocs.io/en/latest/nowcast_system/workers.html#creatingnowcastworkermodules
    ( worker_failures: line   28) ok        https://nomads.ncep.noaa.gov/pub/data/nccf/com/petss/prod/
    (deployment/arbutus_cloud: line  682) ok        https://polar.ncep.noaa.gov/waves/wavewatch/license.shtml
    (deployment/arbutus_cloud: line  696) ok        https://polar.ncep.noaa.gov/waves/wavewatch/manual.v5.16.pdf
    (         workers: line   12) ok        https://nbviewer.org/github/SalishSeaCast/analysis-doug/blob/main/notebooks/ONC-CTD-DataToERDDAP.ipynb
    ( pkg_development: line   23) ok        https://pre-commit.com
    ( pkg_development: line  189) ok        https://pre-commit.com/
    ( pkg_development: line  598) ok        https://pytest-cov.readthedocs.io/en/latest/
    (deployment/index: line   25) ok        https://salishsea-meopar-docs.readthedocs.io/en/latest/repos_organization.html#salishseanowcast-repo
    ( pkg_development: line  127) ok        https://reshapr.readthedocs.io/en/latest/index.html
    (deployment/index: line   30) ok        https://salishsea-meopar-docs.readthedocs.io/en/latest/results_server/index.html#salishseamodelresultsserver
    (         workers: line  455) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#salishsea_tools.places.PLACES
    (figures/create_fig_module: line  678) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#module-salishsea_tools.places
    (figures/create_fig_module: line  764) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#salishsea_tools.visualisations.contour_thalweg
    (figures/fig_modules: line   59) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#salishsea_tools.viz_tools.set_aspect
    (figures/create_fig_module: line  395) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/index.html#salishseatoolspackage
    (figures/create_fig_module: line  423) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodepublicandprivate
    (figures/create_fig_module: line  413) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodeimports
    (figures/create_fig_module: line  673) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodereturnsimplenamespacesfromfunctions
    (figures/create_fig_module: line  365) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodeautogenerateddocs
    (figures/create_fig_module: line  678) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodesalishseatoolsplaces
    (figures/create_fig_module: line  340) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodestandardcopyrightheaderblock
    (deployment/operations: line   56) ok        https://salishsea.eos.ubc.ca
    (deployment/skookum: line   95) ok        https://salishsea.eos.ubc.ca/
    ( pkg_development: line   23) ok        https://salishsea-nowcast.readthedocs.io/en/latest/
    (figures/site_view_fig_metadata: line   45) ok        https://salishsea-site.readthedocs.io
    (   figures/index: line   36) ok        https://salishsea-site.readthedocs.io/
    (         workers: line  513) ok        https://salishsea.eos.ubc.ca/erddap/griddap/index.html?page=1&itemsPerPage=1000
    (         workers: line    7) ok        https://salishsea-nowcast.readthedocs.io/en/latest/figures/create_fig_module.html#creating-a-figure-module
    ( worker_failures: line   52) ok        https://salishsea.eos.ubc.ca/nemo/nowcast/logs/nowcast.log
    (         workers: line    8) ok        https://salishsea.eos.ubc.ca/storm-surge/
    (           index: line   55) ok        https://salishsea.eos.ubc.ca/erddap/index.html
    (         workers: line    9) ok        https://salishsea.eos.ubc.ca/erddap/tabledap/index.html?page=1&itemsPerPage=1000
    (           index: line   25) ok        https://salishsea.eos.ubc.ca/nemo/
    (deployment/operations: line   68) ok        https://supervisord.org/running.html#running-supervisorctl
    (deployment/operations: line   35) ok        https://supervisord.org/
    ( pkg_development: line  130) ok        https://salishseacmd.readthedocs.io/en/latest/index.html#salishseacmdprocessor
    (deployment/index: line  109) ok        https://salishseacast.slack.com/?redir=%2Farchives%2FC011S7BCWGK
    (         workers: line   12) ok        https://www.eoas.ubc.ca/~rich/#T_Tide
    ( pkg_development: line  126) ok        https://ubc-moad-tools.readthedocs.io/en/latest/index.html
    (         workers: line    1) ok        https://www.ndbc.noaa.gov/data/realtime2/
    ( worker_failures: line   28) ok        https://tidesandcurrents.noaa.gov/waterlevels.html?id=9443090
    ( pkg_development: line   86) ok        https://www.python.org/
    (deployment/arbutus_cloud: line   25) ok        https://www.openstack.org/
    (           index: line  120) ok        https://www.apache.org/licenses/LICENSE-2.0
    ( pkg_development: line  222) ok        https://www.sphinx-doc.org/en/master/
    ( pkg_development: line  222) ok        https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
    (figures/create_fig_module: line  546) ok        https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html#info-field-lists
    (deployment/arbutus_cloud: line   25) ok        https://www.oceannetworks.ca/
    (   figures/index: line   23) ok        https://salishsea.eos.ubc.ca/nemo/results/
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

Use:

.. code-block:: console

    $ cd SalishSeaNowcast/
    $ pixi run -e test pytest

to run the test suite.
The output looks something like:

.. code-block:: text
   :class: no-copybutton

    ================================ test session starts =================================
    platform linux -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
    Using --randomly-seed=1914058026
    rootdir: /media/doug/warehouse/MEOPAR/SalishSeaNowcast
    configfile: pyproject.toml
    plugins: httpx-0.36.2, randomly-3.15.0, anyio-4.14.1, cov-7.1.0
    collected 2036 items

    tests/workers/test_collect_weather.py ................................................
    .....                                                                           [  2%]
    tests/workers/test_update_forecast_datasets.py .......................................
    ...............................                                                 [  6%]
    tests/workers/test_make_plots.py .....................................................
    ............                                                                    [  9%]
    tests/workers/test_download_wwatch3_results.py ..........                       [  9%]
    tests/workers/test_make_forcing_links.py .............................................
    .................                                                               [ 12%]
    tests/workers/test_ping_erddap.py .................................             [ 14%]
    tests/workers/test_collect_NeahBay_ssh.py ...................                   [ 15%]
    tests/workers/test_run_NEMO.py .......................................................
    .............................................................................   [ 21%]
    tests/workers/test_collect_river_data.py .............................          [ 23%]
    tests/test_analyze.py .................                                         [ 24%]
    tests/workers/test_make_CHS_currents_file.py ........................           [ 25%]
    tests/workers/test_run_ww3.py ........................................................
    .............                                                                   [ 28%]
    tests/workers/test_grib_to_netcdf.py .................................................
    ............                                                                    [ 31%]
    tests/workers/test_make_feeds.py ...................                            [ 32%]
    tests/workers/test_make_averaged_dataset.py ..................................
    ........                                                                        [ 34%]
    tests/test_next_workers.py ...........................................................
    ......................................................................................
    ........................................                                        [ 43%]
    ......................................................................................
    .......................................                                         [ 49%]
    tests/release_mgmt/test_tag_release.py .........                                [ 50%]
    tests/test_residuals.py ...                                                     [ 50%]
    tests/test_daily_river_flows.py ......................................          [ 52%]
    tests/workers/test_make_ww3_wind_file.py ........................               [ 53%]
    tests/workers/test_watch_NEMO.py .....................................................
    .........................                                                       [ 57%]
    tests/workers/test_upload_forcing.py .................................................
    .......................                                                         [ 60%]
    tests/workers/test_make_turbidity_file.py ....                                  [ 61%]
    tests/workers/test_watch_NEMO_hindcast.py ............................................
    .................                                                               [ 64%]
    tests/workers/test_download_weather.py ...............................................
    .........                                                                       [ 66%]
    tests/workers/test_get_onc_ctd.py ............                                  [ 67%]
    tests/workers/test_make_runoff_file.py ...............................................
    ...........................................................................     [ 73%]
    tests/workers/test_get_vfpa_hadcp.py ..............                             [ 74%]
    tests/workers/test_rotate_hindcast_logs.py ..........                           [ 74%]
    tests/workers/test_make_ssh_file.py .................                           [ 75%]
    tests/workers/test_get_onc_ferry.py ..................................          [ 77%]
    tests/workers/test_make_ww3_current_file.py ...............................     [ 78%]
    tests/workers/test_make_surface_current_tiles.py ...........................    [ 79%]
    tests/workers/test_watch_ww3.py ..................                              [ 80%]
    tests/workers/test_make_live_ocean_files.py .........                           [ 81%]
    tests/workers/test_archive_tarball.py ........................                  [ 82%]
    tests/workers/test_watch_NEMO_agrif.py ..................                       [ 83%]
    tests/workers/test_download_results.py ...............................................
    ...................                                                             [ 86%]
    tests/workers/test_launch_remote_worker.py ............                         [ 87%]
    tests/test_config.py ..............................                             [ 88%]
    tests/workers/test_download_live_ocean.py .........                             [ 89%]
    tests/workers/test_crop_gribs.py .............................................. [ 91%]
    tests/workers/test_run_NEMO_agrif.py ......................                     [ 92%]
    tests/workers/test_run_NEMO_hindcast.py ..............................................
    ......................................................................................
    ..........                                                                      [ 99%]
    tests/workers/test_split_results.py .............                               [100%]

    =============================== 2036 passed in 24.51s ================================

You can monitor what lines of code the test suite exercises using the `coverage.py`_ and `pytest-cov`_ tools with the command:

.. _coverage.py: https://coverage.readthedocs.io/en/latest/
.. _pytest-cov: https://pytest-cov.readthedocs.io/en/latest/

.. code-block:: console

    $ cd SalishSeaNowcast/
    $ pixi run -e test pytest-cov

The test coverage report will be displayed below the test suite run output.

Alternatively,
you can use

.. code-block:: console

    $ pixi run -e test pytest-cov-html

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
