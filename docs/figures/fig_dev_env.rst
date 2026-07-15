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


.. _NowcastFiguresDevEnv:

***************************************
Nowcast Figures Development Environment
***************************************

:py:obj:`SalishSeaNowcast` uses Pixi_ for package and environment management.
If you don't already have Pixi_ installed,
please follow its `installation instructions`_ to do so.

.. _Pixi: https://pixi.prefix.dev/latest/
.. _`installation instructions`: https://pixi.prefix.dev/latest/installation/

Use :command:`pixi install -e fig-dev` command to download the package dependencies for the
figure development and link them into the environment named ``fig-dev``.

Most commands are executed using :command:`pixi run` in the :file:`SalishSeaNowcast/` directory
(or a sub-directory).

* The ``fig-dev`` environment has the packages installed that are required to run the
  commands needed to develop and test figures.
  For example,
  to see the information about how to run the :py:mod:`~nowcast.workers.make_plots` worker,
  use the command
  :command:`pixi run -e fig-dev python -m nowcast.workers.make_plots --help`

* Other environments used for other :ref:`SalishSeaNowcastPackagedDevelopment` tasks have addition packages for running
  the test suite,
  building and link checking the documentation,
  etc.

* If you are using an integrated development environment like VSCode or PyCharm
  where you need a Python interpreter to support coding assistance features,
  run development tasks,
  etc.,
  use the interpreter in the ``fig-dev`` environment.
  You can get its full path with :command:`pixi run -e fig-dev which python`

You can launch a sub-shell in the ``fig-dev`` environment with a command like :command:`pixi shell -e fig-dev`.
That is convenient if you are running a lot of commands because it removed the need to type
:command:`pixi run -e fig-dev` before each of them.
Use :command:`exit` to leave the sub-shell.

:py:obj:`SalishSeaNowcast` figure development depends on a collection of other Python packages
developed by the SalishSeaCast project and friends:

* `NEMO_Nowcast`_
* `moad_tools`_
* `Reshapr`_
* :ref:`SalishSeaToolsPackage`
* `NEMO-Cmd`_
* :ref:`SalishSeaCmdProcessor`
* `salishsea-site`_

.. _NEMO_Nowcast: https://nemo-nowcast.readthedocs.io/en/latest/index.html
.. _moad_tools: https://ubc-moad-tools.readthedocs.io/en/latest/index.html
.. _Reshapr: https://reshapr.readthedocs.io/en/latest/index.html
.. _NEMO-Cmd: https://nemo-cmd.readthedocs.io/en/latest/
.. _salishsea-site: https://github.com/SalishSeaCast/salishsea-site

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
