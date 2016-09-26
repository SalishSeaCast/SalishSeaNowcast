.. Copyright 2013-2016 The Salish Sea MEOPAR contributors
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

.. _SalishSeaNowcastPythonVersions:

Python Versions
===============

The :kbd:`SalishSeaNowcast` package is developed and tested using `Python`_ 3.5 or later.

.. _Python: https://www.python.org/


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

.. code-block:: bash

    $ cd SalishSeaNowcast
    $ conda env create -f environment-dev.yaml
    $ source activate salishsea-nowcast
    (salishsea-nowcast)$ pip install --editable .

The :kbd:`--editable` option in the :command:`pip install` command above installs the :kbd:`SalishSeaNowcast` package from the cloned repo via symlinks so that the installed package will be automatically updated as the repo evolves.

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

  ============================ test session starts ============================
  platform linux -- Python 3.5.1, pytest-2.9.2, py-1.4.31, pluggy-0.3.1
  rootdir: /home/doug/warehouse/MEOPAR/SalishSeaNowcast, inifile:
  collected 164 items

  tests/test_next_workers.py ......

  ======================== 6 passed in 0.001 seconds =========================

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
