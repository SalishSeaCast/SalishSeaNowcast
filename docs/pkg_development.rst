.. Copyright 2013-2017 The Salish Sea MEOPAR contributors
.. and The University of British Columbia
..
.. Licensed under the Apache License, Version 2.0 (the "License");
.. you may not use this file except in compliance with the License.
.. You may obtain a copy of the License at
..
..    http://www.apache.org/licenses/LICENSE-2.0
..
.. Unless required by applicable law or agreed to in writing, software
.. distributed under the License is distributed on an "AS IS" BASIS,
.. WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
.. See the License for the specific language governing permissions and
.. limitations under the License.


.. _SalishSeaNowcastPackagedDevelopment:

*******************************************
:kbd:`SalishSeaNowcast` Package Development
*******************************************

The :kbd:`SalishSeaNowcast` package is a collection of Python modules associated with running the Salish Sea NEMO model in a daily nowcast/forecast mode.
The package uses the `NEMO_Nowcast`_ framework to implement the :ref:`SalishSeaNowcastSystem`.

.. _NEMO_Nowcast: http://nemo-nowcast.readthedocs.io/en/latest/


.. _SalishSeaNowcastPythonVersions:

Python Versions
===============

The :kbd:`SalishSeaNowcast` package is developed and tested using `Python`_ 3.6 or later.
The package uses some Python language features that are not available in versions prior to 3.6,
in particular:

* `Formatted string literals`_
  (aka *f-strings*)
* the `file system path protocol`_

.. _Python: https://www.python.org/
.. _Formatted string literals: https://docs.python.org/3/reference/lexical_analysis.html#f-strings
.. _file system path protocol: https://docs.python.org/3/whatsnew/3.6.html#whatsnew36-pep519


.. _SalishSeaNowcastGettingTheCode:

Getting the Code
================

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

.. _ssh key authentication: https://confluence.atlassian.com/bitbucket/set-up-ssh-for-mercurial-728138122.html


.. _SalishSeaNowcastDevelopmentEnvironment:

Development Environment
=======================

Setting up an isolated development environment using `Conda`_ is recommended.
Assuming that you have `Anaconda Python Distribution`_ or `Miniconda3`_ installed,
you can create and activate an environment called :kbd:`salishsea-nowcast` that will have all of the Python packages necessary for development,
testing,
and building the documentation with the commands:

.. _Conda: http://conda.pydata.org/docs/
.. _Anaconda Python Distribution: https://www.continuum.io/downloads
.. _Miniconda3: http://conda.pydata.org/docs/install/quick.html

.. note::
    The :kbd:`SalishSeaNowcast` is presently under development in the :kbd:`NEMO_Nowcast` branch of the repository.
    It is *very important* to switch to that branch before creating the development environment.

:kbd:`SalishSeaNowcast` depends on the `NEMO_Nowcast`_,
:ref:`salishseatools:SalishSeaToolsPackage`,
and :ref:`salishseatools:SalishSeaCmdProcessor` packages.
If you have not done so already,
please clone the `NEMO_Nowcast repo`_ and `Salish Sea MEOPAR tools repo`_.
The commands below assume that they are cloned beside your :kbd:`SalishSeaNowcast` clone.

.. _NEMO_Nowcast repo: https://bitbucket.org/43ravens/nemo_nowcast
.. _Salish Sea MEOPAR tools repo: https://bitbucket.org/salishsea/tools

.. code-block:: bash

    $ cd SalishSeaNowcast
    $ hg update NEMO_Nowcast
    $ conda env create -f environment-dev.yaml
    $ source activate salishsea-nowcast
    (salishsea-nowcast)$ pip install --editable ../NEMO_Nowcast
    (salishsea-nowcast)$ pip install --editable ../tools/SalishSeaTools
    (salishsea-nowcast)$ pip install --editable ../SalishSeaCmd
    (salishsea-nowcast)$ pip install --editable .

The :kbd:`--editable` option in the :command:`pip install` command above installs the packages from the cloned repos via symlinks so that the installed packages will be automatically updated as the repos evolve.

To deactivate the environment use:

.. code-block:: bash

    (salishsea-nowcast)$ source deactivate


.. _SalishSeaNowcastBuildingTheDocumentation:

Building the Documentation
==========================

The documentation for the :kbd:`SalishSeaNowcast` package is written in `reStructuredText`_ and converted to HTML using `Sphinx`_.
Creating a :ref:`SalishSeaNowcastDevelopmentEnvironment` as described above includes the installation of Sphinx.
Building the documentation is driven by the :file:`docs/Makefile`.
With your :kbd:`salishsea-nowcast` development environment activated,
use:

.. _reStructuredText: http://sphinx-doc.org/rest.html
.. _Sphinx: http://sphinx-doc.org/

.. code-block:: bash

    (salishsea-nowcast)$ (cd docs && make clean html)

to do a clean build of the documentation.
The output looks something like::

  rm -rf _build/*
  sphinx-build -b html -d _build/doctrees   . _build/html
  Running Sphinx v1.4.6
  making output directory...
  loading pickled environment... not yet created
  loading intersphinx inventory from http://salishsea-meopar-docs.readthedocs.io/en/latest/objects.inv...
  loading intersphinx inventory from http://salishsea-meopar-tools.readthedocs.io/en/latest/objects.inv...
  loading intersphinx inventory from https://nemo-nowcast.readthedocs.io/en/latest/objects.inv...
  loading intersphinx inventory from https://docs.python.org/3/objects.inv...
  building [mo]: targets for 0 po files that are out of date
  building [html]: targets for 10 source files that are out of date
  updating environment: 10 added, 0 changed, 0 removed
  reading sources... [100%] workers
  looking for now-outdated files... none found
  pickling environment... done
  checking consistency... done
  preparing documents... done
  writing output... [100%] workers
  generating indices...
  writing additional pages... search
  copying images... [100%] ProcessFlow.svg
  copying static files... done
  copying extra files... done
  dumping search index in English (code: en) ... done
  dumping object inventory... done
  build succeeded.

  Build finished. The HTML pages are in _build/html.

The HTML rendering of the docs ends up in :file:`docs/_build/html/`.
You can open the :file:`index.html` file in that directory tree in your browser to preview the results of the build.

If you have write access to the `repository`_ on Bitbucket,
whenever you push changes to Bitbucket the documentation is automatically re-built and rendered at http://salishsea-nowcast.readthedocs.io/en/nemo_nowcast/.


.. _SalishSeaNowcastRunningTheUnitTests:

Running the Unit Tests
======================

The test suite for the :kbd:`SalishSeaNowcast` package is in :file:`SalishSeaNowcast/tests/`.
The `pytest`_ tool is used for test parametrization and as the test runner for the suite.

.. _pytest: http://pytest.org/latest/

With your :kbd:`salishsea-nowcast` development environment activated,
use:

.. code-block:: bash

    (salishsea-nowcast)$ cd SalishSeaNowcast/
    (salishsea-nowcast)$ py.test

to run the test suite.
The output looks something like::

  =========================== test session starts ===========================
  platform linux -- Python 3.6.0, pytest-3.0.5, py-1.4.32, pluggy-0.4.0
  rootdir: /home/doug/MEOPAR/SalishSeaNowcast, inifile:
  collected 548 items

  tests/test_analyze.py .................
  tests/test_next_workers.py ................................................................................................................................................
  tests/test_residuals.py ...
  tests/workers/test_download_live_ocean.py ........
  tests/workers/test_download_results.py .....................
  tests/workers/test_download_weather.py ..............................
  tests/workers/test_get_NeahBay_ssh.py ..................
  tests/workers/test_get_onc_ctd.py ....................
  tests/workers/test_grib_to_netcdf.py ............
  tests/workers/test_make_feeds.py .......................
  tests/workers/test_make_forcing_links.py ...........................
  tests/workers/test_make_live_ocean_files.py ........
  tests/workers/test_make_plots.py .........................
  tests/workers/test_make_runoff_file.py .......
  tests/workers/test_ping_erddap.py .................................................
  tests/workers/test_run_NEMO.py ...........................................................................
  tests/workers/test_split_results.py ........
  tests/workers/test_upload_forcing.py .................
  tests/workers/test_watch_NEMO.py ....................................

  ======================= 444 passed in 4.13 seconds ========================

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

The :kbd:`SalishSeaNowcast` package code and documentation source files are available as a `Mercurial`_ repository at https://bitbucket.org/salishsea/salishseanowcast.

.. _Mercurial: https://www.mercurial-scm.org/


.. _SalishSeaNowcastIssueTracker:

Issue Tracker
=============

Development tasks,
bug reports,
and enhancement ideas are recorded and managed in the issue tracker at https://bitbucket.org/salishsea/salishseanowcast/issues.
