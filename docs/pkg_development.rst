..  Copyright 2013-2019 The Salish Sea MEOPAR contributors
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
.. image:: https://img.shields.io/badge/python-3.6-blue.svg
    :target: https://docs.python.org/3.6/
    :alt: Python Version
.. image:: https://img.shields.io/badge/version%20control-hg-blue.svg
    :target: https://bitbucket.org/salishsea/salishseanowcast/
    :alt: Mercurial on Bitbucket
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://black.readthedocs.io/en/stable/
    :alt: The uncompromising Python code formatter
.. image:: https://readthedocs.org/projects/salishsea-nowcast/badge/?version=latest
    :target: https://salishsea-nowcast.readthedocs.io/en/latest/
    :alt: Documentation Status
.. image:: https://img.shields.io/bitbucket/issues/salishsea/salishseanowcast.svg
    :target: https://bitbucket.org/salishsea/salishseanowcast/issues?status=new&status=open
    :alt: Issue Tracker

The :kbd:`SalishSeaNowcast` package is a collection of Python modules associated with running the Salish Sea NEMO model in a daily nowcast/forecast mode.
The package uses the `NEMO_Nowcast`_ framework to implement the :ref:`SalishSeaNowcastSystem`.

.. _NEMO_Nowcast: https://nemo-nowcast.readthedocs.io/en/latest/


.. _SalishSeaNowcastPythonVersions:

Python Versions
===============

.. image:: https://img.shields.io/badge/python-3.6-blue.svg
    :target: https://docs.python.org/3.6/
    :alt: Python Version

The :kbd:`SalishSeaNowcast` package is developed and tested using `Python`_ 3.6 or later.
The package uses some Python language features that are not available in versions prior to 3.6,
in particular:

* `formatted string literals`_
  (aka *f-strings*)
* the `file system path protocol`_

.. _Python: https://www.python.org/
.. _formatted string literals: https://docs.python.org/3/reference/lexical_analysis.html#f-strings
.. _file system path protocol: https://docs.python.org/3/whatsnew/3.6.html#whatsnew36-pep519


.. _SalishSeaNowcastGettingTheCode:

Getting the Code
================

.. image:: https://img.shields.io/badge/version%20control-hg-blue.svg
    :target: https://bitbucket.org/salishsea/salishseanowcast/
    :alt: Mercurial on Bitbucket

Clone the code and documentation `repository`_ from Bitbucket with:

.. _repository: https://bitbucket.org/salishsea/salishseanowcast

.. code-block:: bash

    $ hg clone ssh://hg@bitbucket.org/salishsea/salishseanowcast SalishSeaNowcast

or

.. code-block:: bash

    $ hg clone https://your_userid@bitbucket.org/salishsea/salishseanowcast SalishSeaNowcast

if you don't have `ssh key authentication`_ set up on Bitbucket
(replace :kbd:`you_userid` with you Bitbucket userid,
or copy the link from the :guilabel:`Clone` action pop-up on the `repository`_ page).

.. _ssh key authentication: https://confluence.atlassian.com/bitbucket/set-up-an-ssh-key-728138079.html


.. _SalishSeaNowcastDevelopmentEnvironment:

Development Environment
=======================

Setting up an isolated development environment using `Conda`_ is recommended.
Assuming that you have the `Anaconda Python Distribution`_ or `Miniconda3`_ installed,
you can create and activate an environment called :kbd:`salishsea-nowcast` that will have all of the Python packages necessary for development,
testing,
and building the documentation with the commands below.

.. _Conda: https://conda.io/docs/
.. _Anaconda Python Distribution: https://www.anaconda.com/download/
.. _Miniconda3: https://conda.io/docs/install/quick.html

:kbd:`SalishSeaNowcast` depends on the `NEMO_Nowcast`_,
:ref:`SalishSeaToolsPackage`,
`NEMO-Cmd`_,
and :ref:`SalishSeaCmdProcessor` packages.
If you have not done so already,
please clone the `NEMO-Cmd repo`_,
`NEMO_Nowcast repo`_,
and `Salish Sea MEOPAR tools repo`_.
The commands below assume that they are cloned beside your :kbd:`SalishSeaNowcast` clone.

.. _NEMO-Cmd: https://nemo-cmd.readthedocs.io/en/latest/
.. _NEMO-Cmd repo: https://bitbucket.org/salishsea/nemo-cmd
.. _NEMO_Nowcast repo: https://bitbucket.org/43ravens/nemo_nowcast
.. _Salish Sea MEOPAR tools repo: https://bitbucket.org/salishsea/tools

.. code-block:: bash

    $ cd SalishSeaNowcast
    $ hg update NEMO_Nowcast
    $ conda env create -f environment-dev.yaml
    $ source activate salishsea-nowcast
    (salishsea-nowcast)$ pip install --editable ../NEMO_Nowcast
    (salishsea-nowcast)$ pip install --editable ../tools/SalishSeaTools
    (salishsea-nowcast)$ pip install --editable ../NEMO-Cmd
    (salishsea-nowcast)$ pip install --editable ../SalishSeaCmd
    (salishsea-nowcast)$ pip install --editable .

The :kbd:`--editable` option in the :command:`pip install` command above installs the packages from the cloned repos via symlinks so that the installed packages will be automatically updated as the repos evolve.

To deactivate the environment use:

.. code-block:: bash

    (salishsea-nowcast)$ source deactivate


.. _SalishSeaNowcastCodingStyle:

Coding Style
============

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://black.readthedocs.io/en/stable/
    :alt: The uncompromising Python code formatter

The :kbd:`SalishSeaNowcast` package uses the `black`_ code formatting tool to maintain a coding style that is very close to `PEP 8`_.

.. _black: https://black.readthedocs.io/en/stable/
.. _PEP 8: https://www.python.org/dev/peps/pep-0008/

:command:`black` is installed as part of the :ref:`SalishSeaNowcastDevelopmentEnvironment` setup.

To run :command:`black` on the entire code-base use:

.. code-block:: bash

    $ cd SalishSeaNowcast
    $ conda activate salishsea-nowcast
    (salishsea-nowcast)$ black ./

in the repository root directory.
The output looks something like::

  reformatted /media/doug/warehouse/MEOPAR/SalishSeaNowcast/nowcast/next_workers.py
  reformatted /media/doug/warehouse/MEOPAR/SalishSeaNowcast/nowcast/workers/make_CHS_currents_file.py
  reformatted /media/doug/warehouse/MEOPAR/SalishSeaNowcast/tests/test_make_CHS_currents_file.py
  reformatted /media/doug/warehouse/MEOPAR/SalishSeaNowcast/tests/test_next_workers.py
  All done! ✨ 🍰 ✨
  4 files reformatted, 117 files left unchanged.


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

.. _reStructuredText: http://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
.. _Sphinx: http://www.sphinx-doc.org/en/master/

.. code-block:: bash

    (salishsea-nowcast)$ (cd docs && make clean html)

to do a clean build of the documentation.
The output looks something like::

  Removing everything under '_build'...
  Running Sphinx v1.7.6
  making output directory...
  loading pickled environment... not yet created
  loading intersphinx inventory from https://docs.python.org/3/objects.inv...
  loading intersphinx inventory from https://nemo-nowcast.readthedocs.io/en/latest/objects.inv...
  loading intersphinx inventory from https://salishsea-meopar-docs.readthedocs.io/en/latest/objects.inv...
  loading intersphinx inventory from https://salishsea-meopar-tools.readthedocs.io/en/latest/objects.inv...
  loading intersphinx inventory from https://salishsea-site.readthedocs.io/en/latest/objects.inv...
  loading intersphinx inventory from https://salishseacmd.readthedocs.io/en/latest/objects.inv...
  building [mo]: targets for 0 po files that are out of date
  building [html]: targets for 20 source files that are out of date
  updating environment: 20 added, 0 changed, 0 removed
  /media/doug/warehouse/conda_envs/nowcast-sphinx-build/lib/python3.6/site-packages/matplotlib/__init__.py:1357: UserWarning:  This call to matplotlib.use() has no effect
  because the backend has already been chosen;
  matplotlib.use() must be called *before* pylab, matplotlib.pyplot,
  or matplotlib.backends is imported for the first time.

    warnings.warn(_use_error_msg)

  looking for now-outdated files... none found
  pickling environment... done
  checking consistency... done
  preparing documents... done
  writing output... [100%] workers
  generating indices...
  highlighting module code... [100%] nowcast.workers.watch_ww3
  writing additional pages... search
  copying images... [100%] ProcessFlow.png
  copying static files... done
  copying extra files... done
  dumping search index in English (code: en) ... done
  dumping object inventory... done
  build succeeded, 1 warnings.

  The HTML pages are in _build/html.

The warning about :kbd:`matplotlib.use()` is expected; see `issue #19`_.

.. _issue #19: https://bitbucket.org/salishsea/salishseanowcast/issues/19

The HTML rendering of the docs ends up in :file:`docs/_build/html/`.
You can open the :file:`index.html` file in that directory tree in your browser to preview the results of the build.

If you have write access to the `repository`_ on Bitbucket,
whenever you push changes to Bitbucket the documentation is automatically re-built and rendered at https://salishsea-nowcast.readthedocs.io/en/latest/.


.. _SalishSeaNowcastLinkCheckingTheDocumentation:

Link Checking the Documentation
-------------------------------

Sphinx also provides a link checker utility which can be run to find broken or redirected links in the docs.
With your :kbd:`salishsea-nowcast` environment activated,
use:

.. code-block:: bash

    (salishsea-nowcast)$ cd SalishSeaNowcast/docs/
    (salishsea-nowcast) docs$ make linkcheck

The output looks something like::

  Running Sphinx v1.7.6
  loading pickled environment... done
  building [mo]: targets for 0 po files that are out of date
  building [linkcheck]: targets for 19 source files that are out of date
  updating environment: 0 added, 1 changed, 0 removed
  reading sources... [100%] worker_failures
  looking for now-outdated files... none found
  pickling environment... done
  checking consistency... done
  preparing documents... done
  writing output... [  5%] config
  writing output... [ 10%] creating_workers
  (line   23) ok        https://nemo-nowcast.readthedocs.io/en/latest/nowcast_system/workers.html#creatingnowcastworkermodules
  (line   23) ok        https://nemo-nowcast.readthedocs.io/en/latest/
  writing output... [ 15%] deployment/index
  (line   28) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#module-nemo_nowcast.manager
  (line   23) ok        https://salishsea-meopar-docs.readthedocs.io/en/latest/repos_organization.html#salishseanowcast-repo
  (line   28) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#module-nemo_nowcast.message_broker
  (line   28) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#module-nemo_nowcast.log_aggregator
  (line   28) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#module-nemo_nowcast.scheduler
  (line   43) ok        http://www.oceannetworks.ca/
  (line   43) ok        https://www.westgrid.ca/support/systems/arbutus
  (line   43) ok        https://en.wikipedia.org/wiki/Ceph_(software)
  (line   28) ok        https://salishsea-meopar-docs.readthedocs.io/en/latest/results_server/index.html#salishseamodelresultsserver
  writing output... [ 21%] deployment/operations
  (line   33) ok        https://circus.readthedocs.io/en/latest/
  (line   54) ok        https://circus.readthedocs.io/en/latest/man/circusctl/
  (line   64) ok        https://circus.readthedocs.io/en/latest/man/circusctl/
  writing output... [ 26%] deployment/orcinus
  writing output... [ 31%] deployment/skookum_salish
  (line  174) ok        https://salishsea-meopar-docs.readthedocs.io/en/latest/repos_organization.html#ss-run-sets-repo
  (line  174) ok        https://salishsea-meopar-docs.readthedocs.io/en/latest/repos_organization.html#ss-run-sets-repo
  writing output... [ 36%] deployment/west_cloud
  (line   34) ok        https://www.computecanada.ca/
  (line   43) redirect  https://west.cloud.computecanada.ca/dashboard/ - with Found to https://west.cloud.computecanada.ca/auth/login/?next=/
  (line   29) redirect  https://west.cloud.computecanada.ca/dashboard/ - with Found to https://west.cloud.computecanada.ca/auth/login/?next=/
  (line   29) ok        https://docs.openstack.org/horizon/queens/user/
  (line   23) ok        https://www.openstack.org/
  (line   43) ok        https://docs.openstack.org/queens/user/
  (line   43) ok        https://docs.computecanada.ca/wiki/Cloud_Quick_Start
  (line  368) ok        https://docs.computecanada.ca/wiki/CC-Cloud_Resources
  (line  502) ok        http://polar.ncep.noaa.gov/waves/wavewatch/license.shtml
  (line  502) ok        http://polar.ncep.noaa.gov/waves/wavewatch/distribution/ - unauthorized
  (line  516) ok        https://www.vagrantup.com/
  (line  380) ok        https://help.ubuntu.com/community/SettingUpNFSHowTo
  (line  408) ok        https://help.ubuntu.com/community/SettingUpNFSHowTo
  (line  611) redirect  https://gitlab.com/mdunphy/FVCOM41 - with Found to https://gitlab.com/users/sign_in
  (line  516) ok        https://bitbucket.org/salishsea/west.cloud-vm
  (line  522) ok        http://polar.ncep.noaa.gov/waves/wavewatch/manual.v5.16.pdf
  (line   97) ok        http://cloud-images.ubuntu.com/trusty/current/trusty-server-cloudimg-amd64-disk1.img
  writing output... [ 42%] figures/create_fig_module
  (line   40) ok        https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/research/TestTracerThalwegAndSurface.ipynb
  (line   34) ok        https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/research/DevelopTracerThalwegAndSurfaceModule.ipynb
  (line   23) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaNowcast/index.html#salishseanowcastpackage
  (line  336) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodestandardcopyrightheaderblock
  (line  359) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodeautogenerateddocs
  (line  389) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/index.html#salishseatoolspackage
  (line  499) ok        https://salishsea.eos.ubc.ca
  (line  407) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodeimports
  (line  668) ok        https://docs.python.org/3/library/types.html#types.SimpleNamespace
  (line  541) ok        http://www.sphinx-doc.org/en/stable/domains.html#info-field-lists
  (line  417) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodepublicandprivate
  (line  668) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodereturnsimplenamespacesfromfunctions
  (line  673) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/python_packaging/library_code.html#librarycodesalishseatoolsplaces
  (line  867) ok        https://www.python.org/dev/peps/pep-0008/
  (line  673) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#module-salishsea_tools.places
  (line  761) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#salishsea_tools.visualisations.contour_thalweg
  (line  867) ok        https://github.com/google/yapf
  writing output... [ 47%] figures/fig_dev_env
  (line   34) ok        https://docs.python.org/3/whatsnew/3.6.html#whatsnew36-pep519
  (line   44) ok        https://www.anaconda.com/download/
  (line   22) ok        https://conda.io/docs/
  (line   32) ok        https://docs.python.org/3/reference/lexical_analysis.html#f-strings
  (line   44) ok        https://conda.io/docs/install/quick.html
  (line   53) ok        https://bitbucket.org/salishsea/tools/
  (line   55) ok        https://bitbucket.org/salishsea/salishseacmd/
  (line   52) ok        https://bitbucket.org/UBC_MOAD/moad_tools
  (line   54) ok        https://bitbucket.org/salishsea/nemo-cmd/
  (line   56) ok        https://bitbucket.org/salishsea/salishseanowcast
  (line   57) ok        https://bitbucket.org/salishsea/salishsea-site
  (line   51) ok        https://bitbucket.org/43ravens/nemo_nowcast/
  writing output... [ 52%] figures/fig_module_tips
  writing output... [ 57%] figures/fig_modules
  (line   55) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#salishsea_tools.viz_tools.set_aspect
  writing output... [ 63%] figures/index
  (line   33) ok        https://salishsea-site.readthedocs.io/en/latest/
  (line   33) ok        https://salishsea.eos.ubc.ca/nemo/results/
  (line   20) ok        https://salishsea.eos.ubc.ca/nemo/results/
  writing output... [ 68%] figures/make_figure_calls
  (line  145) ok        https://docs.python.org/3/library/stdtypes.html#tuple
  (line  148) ok        https://docs.python.org/3/library/stdtypes.html#dict
  (line  117) ok        https://docs.python.org/3/library/stdtypes.html#dict
  (line  132) ok        https://docs.python.org/3/library/stdtypes.html#dict
  writing output... [ 73%] figures/site_view_fig_metadata
  writing output... [ 78%] figures/website_theme
  (line   37) ok        https://bootswatch.com/superhero/
  writing output... [ 84%] index
  (line   50) ok        https://salishsea.eos.ubc.ca/erddap/index.html
  (line   23) ok        https://salishsea.eos.ubc.ca/nemo/
  (line   55) ok        https://www.westgrid.ca/
  (line   23) ok        https://weather.gc.ca/grib/grib2_HRDPS_HR_e.html
  (line   61) ok        https://nemo-nowcast.readthedocs.io/en/latest/architecture/index.html#frameworkarchitecture
  (line   81) ok        https://nemo-nowcast.readthedocs.io/en/latest/architecture/scheduler.html#scheduler
  (line   61) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#nemo-nowcastbuiltinworkers
  (line  113) ok        http://www.apache.org/licenses/LICENSE-2.0
  (line  109) ok        https://bitbucket.org/salishsea/docs/src/tip/CONTRIBUTORS.rst
  writing output... [ 89%] pkg_development
  (line   21) ok        https://docs.python.org/3.6/
  (line   54) ok        https://www.python.org/
  (line   21) ok        https://www.apache.org/licenses/LICENSE-2.0
  (line   21) ok        https://salishsea-nowcast.readthedocs.io/en/latest/
  (line   21) ok        https://bitbucket.org/salishsea/salishseanowcast/issues?status=new&status=open
  (line   21) ok        https://bitbucket.org/salishsea/salishseanowcast/
  (line   90) ok        https://confluence.atlassian.com/bitbucket/set-up-an-ssh-key-728138079.html
  (line   70) ok        https://bitbucket.org/salishsea/salishseanowcast/
  (line  112) ok        https://nemo-cmd.readthedocs.io/en/latest/
  (line  179) ok        http://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
  (line  112) ok        https://bitbucket.org/salishsea/nemo-cmd
  (line  112) ok        https://bitbucket.org/43ravens/nemo_nowcast
  (line  179) ok        http://www.sphinx-doc.org/en/master/
  (line  112) ok        https://bitbucket.org/salishsea/tools
  (line  112) ok        https://salishseacmd.readthedocs.io/en/latest/index.html#salishseacmdprocessor
  (line  320) ok        https://coverage.readthedocs.io/en/latest/
  (line  232) ok        https://bitbucket.org/salishsea/salishseanowcast/issues/19
  (line  368) ok        https://bitbucket.org/salishsea/salishseanowcast/issues
  (line  270) ok        https://docs.pytest.org/en/latest/
  (line  354) ok        https://www.mercurial-scm.org/
  writing output... [ 94%] worker_failures
  (line   59) ok        https://salishsea.eos.ubc.ca/nemo/nowcast/logs/nowcast.log
  (line   30) ok        https://nbviewer.jupyter.org/url/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/SSH_NeahBay.ipynb
  (line   68) ok        https://salishsea.eos.ubc.ca/nemo/nowcast/logs/nowcast.debug.log
  (line   26) ok        http://www.nws.noaa.gov/mdl/etsurge/index.php?page=stn&region=wc&datum=mllw&list=&map=0-48&type=both&stn=waneah
  (line  162) ok        http://dd.weather.gc.ca/model_hrdps/west/grib2/
  (line  162) ok        http://dd.weather.gc.ca/model_hrdps/west/grib2/06/001/
  (line   26) ok        https://tidesandcurrents.noaa.gov/waterlevels.html?id=9443090
  writing output... [100%] workers
  (line   12) ok        http://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/analysis-doug/raw/tip/notebooks/ONC-CTD-DataToERDDAP.ipynb
  (line    9) ok        https://salishsea.eos.ubc.ca/erddap/tabledap/index.html?page=1&itemsPerPage=1000
  (line  326) ok        https://docs.python.org/3/library/logging.html#logging.Logger
  (line  326) ok        https://docs.python.org/3/library/pathlib.html#pathlib.Path
  (line  326) ok        https://docs.python.org/3/library/stdtypes.html#str
  (line  326) ok        https://docs.python.org/3/library/stdtypes.html#str
  (line   44) ok        https://nemo-nowcast.readthedocs.io/en/latest/architecture/message_broker.html#messagebroker
  (line   40) ok        https://nemo-nowcast.readthedocs.io/en/latest/architecture/manager.html#systemmanager
  (line   40) ok        https://nemo-nowcast.readthedocs.io/en/latest/architecture/messaging.html#messagingsystem
  (line  326) ok        https://docs.python.org/3/library/stdtypes.html#list
  (line  333) ok        https://docs.python.org/3/library/stdtypes.html#list
  (line  333) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#nemo_nowcast.message.Message
  (line  333) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#nemo_nowcast.config.Config
  (line  333) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#nemo_nowcast.message.Message
  (line  333) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#nemo_nowcast.config.Config
  (line  351) ok        https://docs.python.org/3/library/datetime.html#datetime.datetime
  (line  351) ok        https://docs.python.org/3/library/datetime.html#datetime.datetime
  (line  333) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#nemo_nowcast.message.Message
  (line   33) ok        https://docs.python.org/3/library/exceptions.html#ValueError
  (line  351) ok        https://docs.python.org/3/library/functions.html#float
  (line  351) ok        https://docs.python.org/3/library/constants.html#None
  (line   12) ok        https://www.eoas.ubc.ca/~rich/#T_Tide
  (line  333) ok        https://nemo-nowcast.readthedocs.io/en/latest/api.html#nemo_nowcast.config.Config
  (line    1) ok        http://climate.weather.gc.ca/
  (line    4) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#salishsea_tools.stormtools.correct_model
  (line   23) ok        https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/publish/TestCompareTidePredictionMaxSSH.ipynb
  (line   25) ok        https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/publish/DevelopCompareTidePredictionMaxSSH.ipynb
  (line    8) ok        https://salishsea.eos.ubc.ca/storm-surge/
  (line  398) ok        https://docs.python.org/3/library/functions.html#int
  (line  351) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#salishsea_tools.stormtools.storm_surge_risk_level
  (line  440) ok        https://docs.python.org/3/library/constants.html#True
  (line  448) ok        https://salishsea.eos.ubc.ca/erddap/griddap/index.html?page=1&itemsPerPage=1000
  (line    9) ok        https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/fvcom/DevelopTideStnWaterLevel.ipynb
  (line    6) ok        https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/fvcom/TestTideStnWaterLevel.ipynb
  (line    7) ok        https://salishsea-nowcast.readthedocs.io/en/latest/figures/create_fig_module.html#creating-a-figure-module
  (line  398) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#salishsea_tools.places.PLACES
  (line    6) ok        https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/wwatch3/TestWaveHeightPeriod.ipynb
  (line    9) ok        https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/wwatch3/DevelopWaveHeightPeriod.ipynb
  (line  462) ok        https://salishsea-meopar-tools.readthedocs.io/en/latest/SalishSeaTools/api.html#salishsea_tools.places.PLACES
  (line    1) ok        https://www.ndbc.noaa.gov/data/realtime2/
  (line    1) ok        https://www.ndbc.noaa.gov/data/realtime2/

  build succeeded.

  Look for any errors in the above output or in _build/linkcheck/output.txt


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
    (salishsea-nowcast)$ py.test

to run the test suite.
The output looks something like::

  =========================== test session starts ===========================
  platform linux -- Python 3.6.2, pytest-3.2.1, py-1.4.34, pluggy-0.4.0
  rootdir: /home/doug/Documents/MEOPAR/SalishSeaNowcast, inifile:
  collected 833 items

  tests/test_analyze.py .................
  tests/test_next_workers.py .......................................................................................................................................................................................
  tests/test_residuals.py ...
  tests/workers/test_download_live_ocean.py ........
  tests/workers/test_download_results.py .....................
  tests/workers/test_download_weather.py ..............................
  tests/workers/test_get_NeahBay_ssh.py ..................
  tests/workers/test_get_onc_ctd.py ................
  tests/workers/test_get_onc_ferry.py ........
  tests/workers/test_grib_to_netcdf.py ............
  tests/workers/test_make_feeds.py ........................
  tests/workers/test_make_forcing_links.py ......................................
  tests/workers/test_make_live_ocean_files.py ........
  tests/workers/test_make_plots.py ..........................
  tests/workers/test_make_runoff_file.py .......
  tests/workers/test_make_turbidity_file.py .......
  tests/workers/test_make_ww3_current_file.py .......................
  tests/workers/test_make_ww3_wind_file.py .................
  tests/workers/test_ping_erddap.py .......................................
  tests/workers/test_run_NEMO.py ......................................................................................................................................
  tests/workers/test_run_ww3.py ..........................................
  tests/workers/test_split_results.py ........
  tests/workers/test_update_forecast_datasets.py ...............
  tests/workers/test_upload_forcing.py .......................
  tests/workers/test_watch_NEMO.py .......................................................................................
  tests/workers/test_watch_ww3.py ...................

  ======================= 833 passed in 9.03 seconds ========================

You can monitor what lines of code the test suite exercises using the `coverage.py`_ tool with the command:

.. _coverage.py: https://coverage.readthedocs.io/en/latest/

.. code-block:: bash

    (salishsea-nowcast)$ cd SalishSeaNowcast/
    (salishsea-nowcast)$ coverage run -m py.test

and generate a test coverage report with:

.. code-block:: bash

    (salishsea-nowcast)$ coverage report

to produce a plain text report,
or

.. code-block:: bash

    (salishsea-nowcast)$ coverage html

to produce an HTML report that you can view in your browser by opening :file:`SalishSeaNowcast/htmlcov/index.html`.


.. _SalishSeaNowcastVersionControlRepository:

Version Control Repository
==========================

.. image:: https://img.shields.io/badge/version%20control-hg-blue.svg
    :target: https://bitbucket.org/salishsea/salishseanowcast/
    :alt: Mercurial on Bitbucket

The :kbd:`SalishSeaNowcast` package code and documentation source files are available as a `Mercurial`_ repository at https://bitbucket.org/salishsea/salishseanowcast.

.. _Mercurial: https://www.mercurial-scm.org/


.. _SalishSeaNowcastIssueTracker:

Issue Tracker
=============

.. image:: https://img.shields.io/bitbucket/issues/salishsea/salishseanowcast.svg
    :target: https://bitbucket.org/salishsea/salishseanowcast/issues?status=new&status=open
    :alt: Issue Tracker

Development tasks,
bug reports,
and enhancement ideas are recorded and managed in the issue tracker at https://bitbucket.org/salishsea/salishseanowcast/issues.


License
=======

.. image:: https://img.shields.io/badge/license-Apache%202-cb2533.svg
    :target: https://www.apache.org/licenses/LICENSE-2.0
    :alt: Licensed under the Apache License, Version 2.0

The Salish Sea NEMO model nowcast system code and documentation are Copyright 2013-2019 by the `Salish Sea MEOPAR Project Contributors`_ and The University of British Columbia.

.. _Salish Sea MEOPAR Project Contributors: https://bitbucket.org/salishsea/docs/src/tip/CONTRIBUTORS.rst

They are licensed under the Apache License, Version 2.0.
http://www.apache.org/licenses/LICENSE-2.0
Please see the LICENSE file for details of the license.
