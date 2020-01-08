..  Copyright 2013-2020 The Salish Sea MEOPAR contributors
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

.. _NowcastFiguresDevEnv:

***************************************
Nowcast Figures Development Environment
***************************************

This section explains how to set up an isolated `Conda`_ environment for nowcast web site figure development and testing.
The environment will have both the :kbd:`SalishSeaNowcast` nowcast system package,
and the :kbd:`salishsea-site` web site app package installed in it,
along with all of their dependencies.

.. _Conda: https://conda.io/docs/

The :kbd:`SalishSeaNowcast` and :kbd:`salishsea-site` packages use some Python language features that are not available in versions prior to Python 3.6,
in particular:

* `formatted string literals`_
  (aka *f-strings*)
* the `file system path protocol`_

.. _Python: https://www.python.org/
.. _formatted string literals: https://docs.python.org/3/reference/lexical_analysis.html#f-strings
.. _file system path protocol: https://docs.python.org/3/whatsnew/3.6.html#whatsnew36-pep519

Figure development and web site operation both require access to the Salish Sea project :file:`/results/` directory tree.
So,
you should set up this environment on a Waterhole "fish" machine.

The following instructions assume that you have the `Anaconda Python Distribution`_ or `Miniconda3`_ installed.

.. _Anaconda Python Distribution: https://www.anaconda.com/download/
.. _Miniconda3: https://conda.io/docs/install/quick.html

You will also need up-to-date clones of the following repositories from Bitbucket:

* NEMO_Nowcast: https://bitbucket.org/43ravens/nemo_nowcast/
* moad_tools: https://bitbucket.org/UBC_MOAD/moad_tools
* tools: https://bitbucket.org/salishsea/tools/
* NEMO-Cmd :https://bitbucket.org/salishsea/nemo-cmd/
* SalishSeaCmd: https://bitbucket.org/salishsea/salishseacmd/
* SalishSeaNowcast: https://bitbucket.org/salishsea/salishseanowcast
* salishsea-site: https://bitbucket.org/salishsea/salishsea-site

Assuming that all of those repositories are cloned,
one beside the other,
in a directory like :file:`MEOPAR/`,
and with the capitalization shown on the left above,
you can create and activate a figures development environment with these commands:

.. code-block:: bash

    $ cd SalishSeaNowcast
    $ conda env create -f env/environment-fig-dev.yaml
    $ source activate nowcast-fig-dev
    (nowcast-fig-dev)$ pip install --editable ../NEMO_Nowcast
    (nowcast-fig-dev)$ pip install --editable ../moad_tools
    (nowcast-fig-dev)$ pip install --editable ../tools/SalishSeaTools
    (nowcast-fig-dev)$ pip install --editable ../NEMO-Cmd
    (nowcast-fig-dev)$ pip install --editable ../SalishSeaCmd
    (nowcast-fig-dev)$ pip install --editable ../salishsea-site/
    (nowcast-fig-dev)$ pip install --editable .

The :kbd:`--editable` option in the :command:`pip install` command above installs the packages from the cloned repos via symlinks so that the installed packages will be automatically updated as the repos evolve.

To deactivate the environment use:

.. code-block:: bash

    (nowcast-fig-dev)$ source deactivate
