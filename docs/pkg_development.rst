..  Copyright 2013-2021 The Salish Sea MEOPAR contributors
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

.. _SalishSeaNowcastPackagedDevelopment:

*******************************************
:kbd:`SalishSeaNowcast` Package Development
*******************************************

.. image:: https://img.shields.io/badge/license-Apache%202-cb2533.svg
    :target: https://www.apache.org/licenses/LICENSE-2.0
    :alt: Licensed under the Apache License, Version 2.0
.. image:: https://img.shields.io/badge/python-3.10-blue.svg
    :target: https://docs.python.org/3.10/
    :alt: Python Version
.. image:: https://img.shields.io/badge/version%20control-git-blue.svg?logo=github
    :target: https://github.com/SalishSeaCast/SalishSeaNowcast
    :alt: Git on GitHub
.. image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://black.readthedocs.io/en/stable/
    :alt: The uncompromising Python code formatter
.. image:: https://readthedocs.org/projects/salishsea-nowcast/badge/?version=latest
    :target: https://salishsea-nowcast.readthedocs.io/en/latest/
    :alt: Documentation Status
.. image:: https://github.com/SalishSeaCast/SalishSeaNowcast/workflows/sphinx-linkcheck/badge.svg
      :target: https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:sphinx-linkcheck
      :alt: Sphinx linkcheck
.. image:: https://github.com/SalishSeaCast/SalishSeaNowcast/workflows/CI/badge.svg
    :target: https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:CI
    :alt: pytest and test coverage analysis
.. image:: https://codecov.io/gh/SalishSeaCast/SalishSeaNowcast/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/SalishSeaCast/SalishSeaNowcast
    :alt: Codecov Testing Coverage Report
.. image:: https://github.com/SalishSeaCast/SalishSeaNowcast/actions/workflows/codeql-analysis.yaml/badge.svg
      :target: https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:CodeQL
      :alt: CodeQL analysis
.. image:: https://img.shields.io/github/issues/SalishSeaCast/SalishSeaNowcast?logo=github
    :target: https://github.com/SalishSeaCast/SalishSeaNowcast/issues
    :alt: Issue Tracker

The :kbd:`SalishSeaNowcast` package is a collection of Python modules associated with running the Salish Sea NEMO model in a daily nowcast/forecast mode.
The package uses the `NEMO_Nowcast`_ framework to implement the :ref:`SalishSeaNowcastSystem`.

.. _NEMO_Nowcast: https://nemo-nowcast.readthedocs.io/en/latest/


.. _SalishSeaNowcastPythonVersions:

Python Versions
===============

.. image:: https://img.shields.io/badge/python-3.10-blue.svg
    :target: https://docs.python.org/3.10/
    :alt: Python Version

The :kbd:`SalishSeaNowcast` package is developed and tested using `Python`_ 3.10.


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
you can create and activate an environment called :kbd:`salishsea-nowcast` that will have all of the Python packages necessary for development,
testing,
and building the documentation with the commands below.

.. _Conda: https://conda.io/en/latest/
.. _Miniconda: https://docs.conda.io/en/latest/miniconda.html

:kbd:`SalishSeaNowcast` depends on a collection of other Python packages developed by the SalishSeaCast project and friends:

* `NEMO_Nowcast`_
* `moad_tools`_
* :ref:`SalishSeaToolsPackage`
* `OPPTools`_
* `NEMO-Cmd`_
* :ref:`SalishSeaCmdProcessor`
* `FVCOM-Cmd`_

.. _moad_tools: https://ubc-moad-tools.readthedocs.io/en/latest/index.html
.. _OPPTools: https://gitlab.com/mdunphy/OPPTools
.. _NEMO-Cmd: https://nemo-cmd.readthedocs.io/en/latest/
.. _FVCOM-Cmd: https://github.com/SalishSeaCast/FVCOM-Cmd

If you have not done so already,
you can clone those repos with:

.. code-block:: bash

    $ cd SalishSeaNowcast/..
    $ git clone git@github.com:43ravens/NEMO_Nowcast.git
    $ git clone git@github.com:UBC-MOAD/moad_tools.git
    $ git clone git@github.com:SalishSeaCast/tools.git
    $ git clone git@gitlab.com:mdunphy/OPPTools.git
    $ git clone git@github.com:SalishSeaCast/NEMO-Cmd.git
    $ git clone git@github.com:SalishSeaCast/SalishSeaCmd.git
    $ git clone git@github.com:SalishSeaCast/FVCOM-Cmd.git

If you already have clones of those repos,
please ensure that they are up to date.

Assuming that those repos are cloned beside your :kbd:`SalishSeaNowcast` clone,
the commands below install the packages into your :kbd:`salishsea-nowcast` development environment.

.. code-block:: bash

    $ cd SalishSeaNowcast
    $ conda env create -f envs/environment-dev.yaml
    $ conda activate salishsea-nowcast
    (salishsea-nowcast)$ python3 -m pip install --editable ../NEMO_Nowcast
    (salishsea-nowcast)$ python3 -m pip install --editable ../moad_tools
    (salishsea-nowcast)$ python3 -m pip install --editable ../tools/SalishSeaTools
    (salishsea-nowcast)$ python3 -m pip install --editable ../OPPTools
    (salishsea-nowcast)$ python3 -m pip install --editable ../NEMO-Cmd
    (salishsea-nowcast)$ python3 -m pip install --editable ../SalishSeaCmd
    (salishsea-nowcast)$ python3 -m pip install --editable ../FVCOM-Cmd
    (salishsea-nowcast)$ python3 -m pip install --editable .

The :kbd:`--editable` option in the :command:`pip install` command above installs the packages from the cloned repos via symlinks so that the installed packages will be automatically updated as the repos evolve.

To deactivate the environment use:

.. code-block:: bash

    (salishsea-nowcast)$ conda deactivate


.. _SalishSeaNowcastCodingStyle:

Coding Style
============

.. image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://black.readthedocs.io/en/stable/
    :alt: The uncompromising Python code formatter

The :kbd:`SalishSeaNowcast` package uses Git pre-commit hooks managed by `pre-commit`_ to maintain consistent code style and and other aspects of code,
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

.. note:: You only need to install the hooks once immediately after you make a new clone of the `SalishSeaNowcast repository`_ and build your :ref:`SalishSeaNowcastDevelopmentEnvironment`.

.. _SalishSeaNowcast repository: https://github.com/SalishSeaCast/SalishSeaNowcast


.. _SalishSeaNowcastBuildingTheDocumentation:

Building the Documentation
==========================

.. image:: https://readthedocs.org/projects/salishsea-nowcast/badge/?version=latest
    :target: https://salishsea-nowcast.readthedocs.io/en/latest/
    :alt: Documentation Status

The documentation for the :kbd:`SalishSeaNowcast` package is written in `reStructuredText`_ and converted to HTML using `Sphinx`_.
Creating a :ref:`SalishSeaNowcastDevelopmentEnvironment` as described above includes the installation of Sphinx.
Building the documentation is driven by the :file:`docs/Makefile`.
With your :kbd:`salishsea-nowcast` development environment activated,
use:

.. _reStructuredText: https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
.. _Sphinx: https://www.sphinx-doc.org/en/master/

.. code-block:: bash

    (salishsea-nowcast)$ (cd docs && make clean html)

to do a clean build of the documentation.
The output looks something like::

  Removing everything under '_build'...
  Running Sphinx v3.3.1
  making output directory... done
  loading intersphinx inventory from https://docs.python.org/3/objects.inv...
  loading intersphinx inventory from https://nemo-nowcast.readthedocs.io/en/latest/objects.inv...
  loading intersphinx inventory from https://salishsea-meopar-docs.readthedocs.io/en/latest/objects.inv...
  loading intersphinx inventory from https://salishsea-meopar-tools.readthedocs.io/en/latest/objects.inv...
  loading intersphinx inventory from https://salishsea-site.readthedocs.io/en/latest/objects.inv...
  loading intersphinx inventory from https://salishseacmd.readthedocs.io/en/latest/objects.inv...
  building [mo]: targets for 0 po files that are out of date
  building [html]: targets for 20 source files that are out of date
  updating environment: [new config] 20 added, 0 changed, 0 removed
  reading sources... [100%] workers
  looking for now-outdated files... none found
  pickling environment... done
  checking consistency... done
  preparing documents... done
  writing output... [100%] workers
  generating indices... genindex py-modindex done
  highlighting module code... [100%] nowcast.workers.watch_ww3
  writing additional pages... search done
  copying images... [100%] ProcessFlow.png
  copying static files... done
  copying extra files... done
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

.. image:: https://github.com/SalishSeaCast/SalishSeaNowcast/workflows/sphinx-linkcheck/badge.svg
      :target: https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:sphinx-linkcheck
      :alt: Sphinx linkcheck


Sphinx also provides a link checker utility which can be run to find broken or redirected links in the docs.
With your :kbd:`salishsea-nowcast` environment activated,
use:

.. code-block:: bash

    (salishsea-nowcast)$ cd SalishSeaNowcast/docs/
    (salishsea-nowcast) docs$ make linkcheck

The output looks something like::

  Running Sphinx v3.3.1
  making output directory... done
  loading intersphinx inventory from https://docs.python.org/3/objects.inv...
  loading intersphinx inventory from https://nemo-nowcast.readthedocs.io/en/latest/objects.inv...
  loading intersphinx inventory from https://salishsea-meopar-docs.readthedocs.io/en/latest/objects.inv...
  loading intersphinx inventory from https://salishsea-meopar-tools.readthedocs.io/en/latest/objects.inv...
  loading intersphinx inventory from https://salishsea-site.readthedocs.io/en/latest/objects.inv...
  loading intersphinx inventory from https://salishseacmd.readthedocs.io/en/latest/objects.inv...
  building [mo]: targets for 0 po files that are out of date
  building [linkcheck]: targets for 20 source files that are out of date
  updating environment: [new config] 20 added, 0 changed, 0 removed
  reading sources... [100%] workers
  looking for now-outdated files... none found
  pickling environment... done
  checking consistency... done
  preparing documents... done
  writing output... [  5%] config
  writing output... [ 10%] creating_workers
  (line   22) ok        https://nemo-nowcast.readthedocs.io/en/latest/
  (line   22) ok        https://nemo-nowcast.readthedocs.io/en/latest/nowcast_system/workers.html#creatingnowcastworkermodules
  writing output... [ 15%] deployment/arbutus_cloud
  (line   22) ok        https://www.oceannetworks.ca/
  (line   29) ok        https://docs.openstack.org/horizon/stein/user/
  (line   22) ok        https://www.openstack.org/
  (line   22) ok        https://docs.computecanada.ca/wiki/Cloud_resources#Arbutus_cloud_.28arbutus.cloud.computecanada.ca.29
  (line   43) redirect  https://arbutus.cloud.computecanada.ca/ - with Found to https://arbutus.cloud.computecanada.ca/auth/login/?next=/
  (line   34) ok        https://www.computecanada.ca/
  (line   43) ok        https://docs.openstack.org/queens/user/
  (line   43) ok        https://docs.computecanada.ca/wiki/Cloud_Quick_Start
  (line  670) ok        https://polar.ncep.noaa.gov/waves/wavewatch/license.shtml
  (line  684) ok        https://polar.ncep.noaa.gov/waves/wavewatch/manual.v5.16.pdf
  (line  772) ok        https://docs.conda.io/en/latest/miniconda.html
  (line  670) ok        https://polar.ncep.noaa.gov/waves/wavewatch/distribution/ - unauthorized
  (line  419) ok        https://help.ubuntu.com/community/SettingUpNFSHowTo
  (line  755) -ignored- https://gitlab.com/mdunphy/FVCOM41: 503 Server Error: Service Temporarily Unavailable for url: https://gitlab.com/users/sign_in
  writing output... [ 20%] deployment/index
  (line   27) ok        https://salishsea-meopar-docs.readthedocs.io/en/latest/results_server/index.html#salishseamodelresultsserver
  (line   22) ok        https://salishsea-meopar-docs.readthedocs.io/en/latest/repos_organization.html#salishseanowcast-repo
  (line   27) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#module-nemo_nowcast.message_broker
  (line   27) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#module-nemo_nowcast.log_aggregator
  (line   27) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#module-nemo_nowcast.manager
  (line   40) ok        https://en.wikipedia.org/wiki/Ceph_(software)
  (line  103) ok        https://salishseacast.slack.com/?redir=%2Farchives%2FC011S7BCWGK
  writing output... [ 25%] deployment/operations
  (line   53) ok        https://salishsea.eos.ubc.ca
  (line   53) ok        http://supervisord.org/
  (line   32) ok        http://supervisord.org/
  (line   65) ok        http://supervisord.org/running.html#running-supervisorctl
  (line   75) ok        http://supervisord.org/running.html#running-supervisorctl
  (line   32) ok        https://dd.weather.gc.ca/
  (line   95) ok        https://dd.weather.gc.ca/
  (line  119) ok        https://github.com/SalishSeaCast/salishsea-site/actions?query=workflow:deployment
  (line   95) ok        https://github.com/MetPX/sarracenia/blob/master/doc/sr_subscribe.1.rst
  (line   95) ok        https://github.com/MetPX/sarracenia/blob/master/doc/sr_subscribe.1.rst
  (line   32) ok        https://github.com/MetPX/sarracenia/blob/master/doc/sr_subscribe.1.rst
  writing output... [ 30%] deployment/optimum
  writing output... [ 35%] deployment/orcinus
  writing output... [ 40%] deployment/skookum_salish
  (line  329) ok        https://salishsea.eos.ubc.ca/
  (line  129) ok        https://salishsea.eos.ubc.ca/
  (line  275) ok        https://github.com/SalishSeaCast/salishsea-site
  (line  129) ok        https://github.com/SalishSeaCast/salishsea-site
  (line  286) ok        https://github.com/SalishSeaCast/salishsea-site
  writing output... [ 45%] figures/create_fig_module
  (line   22) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaNowcast/index.html#salishseanowcastpackage
  (line  334) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodestandardcopyrightheaderblock
  (line  357) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodeautogenerateddocs
  (line  387) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/index.html#salishseatoolspackage
  (line  405) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodeimports
  (line  415) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodepublicandprivate
  (line  665) ok        https://docs.python.org/3/library/types.html#types.SimpleNamespace
  (line  665) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodereturnsimplenamespacesfromfunctions
  (line  538) ok        https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html#info-field-lists
  (line  670) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodesalishseatoolsplaces
  (line  670) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#module-salishsea_tools.places
  (line  757) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#salishsea_tools.visualisations.contour_thalweg
  (line  863) ok        https://www.python.org/dev/peps/pep-0008/
  (line   39) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/TestTracerThalwegAndSurface.ipynb
  (line   33) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/DevelopTracerThalwegAndSurfaceModule.ipynb
  (line  863) ok        https://github.com/google/yapf
  writing output... [ 50%] figures/fig_dev_env
  (line   34) ok        https://docs.python.org/3/whatsnew/3.6.html#whatsnew36-pep519
  (line   32) ok        https://docs.python.org/3/reference/lexical_analysis.html#f-strings
  (line   22) ok        https://conda.io/en/latest/
  (line   54) ok        https://github.com/SalishSeaCast/SalishSeaCmd
  (line   50) ok        https://github.com/43ravens/NEMO_Nowcast
  (line   53) ok        https://github.com/SalishSeaCast/NEMO-Cmd
  (line   51) ok        https://github.com/UBC-MOAD/moad_tools
  (line   52) ok        https://github.com/SalishSeaCast/tools
  (line   55) ok        https://github.com/SalishSeaCast/SalishSeaNowcast
  writing output... [ 55%] figures/fig_module_tips
  writing output... [ 60%] figures/fig_modules
  (line   59) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#salishsea_tools.viz_tools.set_aspect
  writing output... [ 65%] figures/index
  (line   33) ok        https://salishsea-site.readthedocs.io/en/latest/
  (line   20) ok        https://salishsea.eos.ubc.ca/nemo/results/
  (line   33) ok        https://salishsea.eos.ubc.ca/nemo/results/
  writing output... [ 70%] figures/make_figure_calls
  (line  145) ok        https://docs.python.org/3/library/stdtypes.html#tuple
  (line  117) ok        https://docs.python.org/3/library/stdtypes.html#dict
  (line  148) ok        https://docs.python.org/3/library/stdtypes.html#dict
  (line  132) ok        https://docs.python.org/3/library/stdtypes.html#dict
  writing output... [ 75%] figures/site_view_fig_metadata
  writing output... [ 80%] figures/website_theme
  (line   38) ok        https://bootswatch.com/superhero/
  writing output... [ 85%] index
  (line   54) ok        https://www.westgrid.ca/
  (line   49) ok        https://salishsea.eos.ubc.ca/erddap/index.html
  (line   60) ok        https://nemo-nowcast.readthedocs.io/en/latest/architecture/index.html#frameworkarchitecture
  (line   22) ok        https://salishsea.eos.ubc.ca/nemo/
  (line   60) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#nemo-nowcastbuiltinworkers
  (line   22) ok        https://weather.gc.ca/grib/grib2_HRDPS_HR_e.html
  (line  110) ok        http://www.apache.org/licenses/LICENSE-2.0
  (line  106) ok        https://github.com/SalishSeaCast/docs/blob/master/CONTRIBUTORS.rst
  writing output... [ 90%] pkg_development
  (line   20) ok        https://docs.python.org/3.9/
  (line   20) ok        https://black.readthedocs.io/en/stable/
  (line   20) ok        https://salishsea-nowcast.readthedocs.io/en/latest/
  (line   62) ok        https://www.python.org/
  (line  110) ok        https://ubc-moad-tools.readthedocs.io/en/latest/index.html
  (line   20) ok        https://codecov.io/gh/SalishSeaCast/SalishSeaNowcast
  (line  113) ok        https://nemo-cmd.readthedocs.io/en/latest/
  (line  112) ok        https://gitlab.com/mdunphy/OPPTools
  (line  114) ok        https://salishseacmd.readthedocs.io/en/latest/index.html#salishseacmdprocessor
  (line  209) ok        https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
  (line  209) ok        https://www.sphinx-doc.org/en/master/
  (line   20) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/issues
  (line  475) ok        https://docs.pytest.org/en/latest/
  (line   20) ok        https://www.apache.org/licenses/LICENSE-2.0
  (line  525) ok        https://coverage.readthedocs.io/en/latest/
  (line  525) ok        https://pytest-cov.readthedocs.io/en/latest/
  (line  115) ok        https://github.com/SalishSeaCast/FVCOM-Cmd
  (line  550) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow%3ACI
  (line   20) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow%3ACI
  (line  567) ok        https://docs.github.com/en/free-pro-team@latest/actions
  (line  581) ok        https://git-scm.com/
  (line  262) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/issues/19
  (line   20) ok        https://img.shields.io/badge/license-Apache%202-cb2533.svg
  (line   20) ok        https://img.shields.io/badge/python-3.10-blue.svg
  (line   20) ok        https://img.shields.io/badge/version%20control-git-blue.svg?logo=github
  (line   20) ok        https://img.shields.io/badge/code%20style-black-000000.svg
  (line   20) ok        https://codecov.io/gh/SalishSeaCast/SalishSeaNowcast/branch/master/graph/badge.svg
  (line   20) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/workflows/CI/badge.svg
  (line   20) ok        https://readthedocs.org/projects/salishsea-nowcast/badge/?version=latest
  (line  556) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/actions
  (line  203) ok        https://readthedocs.org/projects/salishsea-nowcast/badge/?version=latest
  (line   20) ok        https://img.shields.io/github/issues/SalishSeaCast/SalishSeaNowcast?logo=github
  (line  556) ok        https://github.com/SalishSeaCast/SalishSeaNowcast/commits/master
  (line  589) ok        https://img.shields.io/github/issues/SalishSeaCast/SalishSeaNowcast?logo=github
  writing output... [ 95%] worker_failures
  (line   58) ok        https://salishsea.eos.ubc.ca/nemo/nowcast/logs/nowcast.log
  (line   67) ok        https://salishsea.eos.ubc.ca/nemo/nowcast/logs/nowcast.debug.log
  (line   25) ok        https://www.nws.noaa.gov/mdl/etsurge/index.php?page=stn&region=wc&datum=mllw&list=&map=0-48&type=both&stn=waneah
  (line  161) ok        https://dd.weather.gc.ca/model_hrdps/west/grib2/06/001/
  (line  161) ok        https://dd.weather.gc.ca/model_hrdps/west/grib2/
  (line   29) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/SSH_NeahBay.ipynb
  (line   25) ok        https://tidesandcurrents.noaa.gov/waterlevels.html?id=9443090
  writing output... [100%] workers
  (line   38) ok        https://nemo-nowcast.readthedocs.io/en/latest/architecture/message_broker.html#messagebroker
  (line   34) ok        https://nemo-nowcast.readthedocs.io/en/latest/architecture/manager.html#systemmanager
  (line    9) ok        https://salishsea.eos.ubc.ca/erddap/tabledap/index.html?page=1&itemsPerPage=1000
  (line   34) ok        https://nemo-nowcast.readthedocs.io/en/latest/architecture/messaging.html#messagingsystem
  (line  362) ok        https://docs.python.org/3/library/pathlib.html#pathlib.Path
  (line  362) ok        https://docs.python.org/3/library/logging.html#logging.Logger
  (line  362) ok        https://docs.python.org/3/library/functions.html#int
  (line  362) ok        https://docs.python.org/3/library/stdtypes.html#str
  (line  362) ok        https://docs.python.org/3/library/functions.html#int
  (line  362) ok        https://docs.python.org/3/library/stdtypes.html#str
  (line  379) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#nemo_nowcast.message.Message
  (line  362) ok        https://docs.python.org/3/library/stdtypes.html#str
  (line  362) ok        https://docs.python.org/3/library/stdtypes.html#list
  (line  379) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#nemo_nowcast.config.Config
  (line  379) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#nemo_nowcast.config.Config
  (line  379) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#nemo_nowcast.config.Config
  (line  379) ok        https://docs.python.org/3/library/stdtypes.html#list
  (line  397) ok        https://docs.python.org/3/library/datetime.html#datetime.datetime
  (line  397) ok        https://docs.python.org/3/library/datetime.html#datetime.datetime
  (line  397) ok        https://docs.python.org/3/library/datetime.html#datetime.datetime
  (line   33) ok        https://docs.python.org/3/library/exceptions.html#ValueError
  (line    4) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#salishsea_tools.stormtools.correct_model
  (line  397) ok        https://docs.python.org/3/library/functions.html#float
  (line  397) ok        https://docs.python.org/3/library/constants.html#None
  (line  397) ok        https://docs.python.org/3/library/functions.html#float
  (line  397) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#salishsea_tools.stormtools.storm_surge_risk_level
  (line  429) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#salishsea_tools.places.PLACES
  (line   12) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/analysis-doug/blob/main/notebooks/ONC-CTD-DataToERDDAP.ipynb
  (line    5) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/fvcom/publish/TestSecondNarrowsCurrent.ipynb
  (line    1) ok        https://climate.weather.gc.ca/
  (line    8) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/fvcom/publish/DevelopSecondNarrowsCurrent.ipynb
  (line    9) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/fvcom/publish/DevelopTideStnWaterLevel.ipynb
  (line   12) ok        https://www.eoas.ubc.ca/~rich/#T_Tide
  (line    5) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/comparison/TestSalinityFerryTrackModule.ipynb
  (line   23) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/publish/TestCompareTidePredictionMaxSSH.ipynb
  (line   10) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/comparison/TestSandHeadsWinds.ipynb
  (line    6) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/fvcom/publish/TestTideStnWaterLevel.ipynb
  (line    8) ok        https://salishsea.eos.ubc.ca/storm-surge/
  (line    4) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/fvcom/research/TestSurfaceCurrents.ipynb
  (line    7) ok        https://salishsea-nowcast.readthedocs.io/en/latest/figures/create_fig_module.html#creating-a-figure-module
  (line   26) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/publish/DevelopCompareTidePredictionMaxSSH.ipynb
  (line  545) ok        https://docs.python.org/3/library/constants.html#True
  (line   11) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/publish/TestPtAtkinsonTideModule.ipynb
  (line  553) ok        https://salishsea.eos.ubc.ca/erddap/griddap/index.html?page=1&itemsPerPage=1000
  (line    1) ok        https://www.ndbc.noaa.gov/data/realtime2/
  (line   11) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/publish/TestStormSurgeAlertsModule.ipynb
  (line   13) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/publish/TestStormSurgeAlertsThumbnailModule.ipynb
  (line    6) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/wwatch3/TestWaveHeightPeriod.ipynb
  (line   10) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/TestTimeSeriesPlots.ipynb
  (line   13) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/DevelopTimeSeriesPlots.ipynb
  (line    9) ok        https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/wwatch3/DevelopWaveHeightPeriod.ipynb

  build succeeded.

  Look for any errors in the above output or in _build/linkcheck/output.txt

:command:`make linkcheck` is run monthly via a `scheduled GitHub Actions workflow`_

.. _scheduled GitHub Actions workflow: https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:sphinx-linkcheck


.. _SalishSeaNowcastRunningTheUnitTests:

Running the Unit Tests
======================

The test suite for the :kbd:`SalishSeaNowcast` package is in :file:`SalishSeaNowcast/tests/`.
The `pytest`_ tool is used for test parametrization and as the test runner for the suite.

.. _pytest: https://docs.pytest.org/en/latest/

With your :kbd:`salishsea-nowcast` development environment activated,
use:

.. code-block:: bash

    (salishsea-nowcast)$ cd SalishSeaNowcast/
    (salishsea-nowcast)$ pytest

to run the test suite.
The output looks something like::

  ============================ test session starts ============================
  platform linux -- Python 3.9.2, pytest-6.2.3, py-1.10.0, pluggy-0.13.1
  Using --randomly-seed=1204534893
  rootdir: /media/doug/warehouse/MEOPAR/SalishSeaNowcast
  plugins: randomly-3.7.0, xdist-2.2.1, forked-1.3.0
  collected 2063 items

  tests/workers/test_make_fvcom_atmos_forcing.py .....................................
  tests/workers/test_upload_fvcom_atmos_forcing.py ..............................
  tests/workers/test_get_onc_ctd.py ...........
  tests/test_residuals.py ...
  tests/workers/test_upload_forcing.py ...............................................
  ..........................
  tests/workers/test_make_surface_current_tiles.py .............................
  tests/workers/test_ping_erddap.py .................................
  tests/workers/test_run_NEMO_hindcast.py ............................................
  ....................................................................................
  ................
  tests/workers/test_collect_river_data.py ............
  tests/workers/test_watch_NEMO.py ...................................................
  .............................................
  tests/workers/test_run_NEMO_agrif.py .................
  tests/workers/test_get_onc_ferry.py .............
  tests/workers/test_split_results.py .............
  tests/workers/test_run_NEMO.py .....................................................
  ....................................................................................
  .................
  tests/workers/test_grib_to_netcdf.py ..................
  tests/workers/test_make_fvcom_rivers_forcing.py ....................................
  tests/workers/test_run_fvcom.py ....................................................
  ................
  tests/workers/test_download_live_ocean.py ..........
  tests/workers/test_download_results.py .............................................
  .............................
  tests/workers/test_make_runoff_file.py ...........
  tests/workers/test_make_turbidity_file.py ......
  tests/workers/test_make_ssh_file.py .................
  tests/test_config.py .............
  tests/workers/test_update_forecast_datasets.py .....................................
  ..............................
  tests/workers/test_make_CHS_currents_file.py .............................
  tests/workers/test_make_forcing_links.py ...........................................
  ..............................
  tests/workers/test_download_wwatch3_results.py ............
  tests/workers/test_watch_fvcom.py ...............................
  tests/test_next_workers.py .........................................................
  ....................................................................................
  ....................................................................................
  ....................................................................................
  ..........................................
  tests/release_mgmt/test_tag_release.py .........
  tests/workers/test_run_ww3.py ......................................................
  ..............
  tests/workers/test_download_weather.py .............................................
  .....................
  tests/workers/test_make_feeds.py .....................
  tests/test_analyze.py .................
  tests/workers/test_make_fvcom_boundary.py .....................................
  tests/workers/test_watch_NEMO_hindcast.py ..........................................
  .....................
  tests/workers/test_collect_weather.py ..............................................
  .......
  tests/workers/test_download_fvcom_results.py .............................
  tests/workers/test_collect_NeahBay_ssh.py ...................
  tests/workers/test_make_live_ocean_files.py ...........
  tests/workers/test_watch_ww3.py ................
  tests/workers/test_make_ww3_current_file.py .................................
  tests/workers/test_make_plots.py ...................................................
  .............
  tests/workers/test_get_vfpa_hadcp.py ...............
  tests/workers/test_watch_NEMO_agrif.py ....................
  tests/workers/test_launch_remote_worker.py ...............
  tests/workers/test_make_ww3_wind_file.py ..........................

  ===================== 2063 passed in 95.74s (0:01:35) ======================

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

.. image:: https://github.com/SalishSeaCast/SalishSeaNowcast/workflows/CI/badge.svg
    :target: https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:CI
    :alt: GitHub Workflow Status

The :kbd:`SalishSeaNowcast` package unit test suite is run and a coverage report is generated whenever changes are pushed to GitHub.
The results are visible on the `repo actions page`_,
from the green checkmarks beside commits on the `repo commits page`_,
or from the green checkmark to the left of the "Latest commit" message on the `repo code overview page`_ .
The testing coverage report is uploaded to `codecov.io`_

.. _repo actions page: https://github.com/SalishSeaCast/SalishSeaNowcast/actions
.. _repo commits page: https://github.com/SalishSeaCast/SalishSeaNowcast/commits/main
.. _repo code overview page: https://github.com/SalishSeaCast/SalishSeaNowcast
.. _codecov.io: https://codecov.io/gh/SalishSeaCast/SalishSeaNowcast

The `GitHub Actions`_ workflow configuration that defines the continuous integration tasks is in the :file:`.github/workflows/pytest-coverage.yaml` file.

.. _GitHub Actions: https://docs.github.com/en/actions


.. _SalishSeaNowcastVersionControlRepository:

Version Control Repository
==========================

.. image:: https://img.shields.io/badge/version%20control-git-blue.svg?logo=github
    :target: https://github.com/SalishSeaCast/SalishSeaNowcast
    :alt: Git on GitHub

The :kbd:`SalishSeaNowcast` package code and documentation source files are available as a `Git`_ repository at https://github.com/SalishSeaCast/SalishSeaNowcast.

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

The Salish Sea NEMO model nowcast system code and documentation are copyright 2013-2021 by the `Salish Sea MEOPAR Project Contributors`_ and The University of British Columbia.

.. _Salish Sea MEOPAR Project Contributors: https://github.com/SalishSeaCast/docs/blob/master/CONTRIBUTORS.rst

They are licensed under the Apache License, Version 2.0.
http://www.apache.org/licenses/LICENSE-2.0
Please see the LICENSE file for details of the license.
