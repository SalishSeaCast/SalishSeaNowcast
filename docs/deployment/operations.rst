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


.. _NowcastSystemOperations:

*************************
Nowcast System Operations
*************************

:command:`ssh` Hosts and Keys Configuration
===========================================

.. TODO::
    Write this section.


Cold Start
==========

The long-running processes in the nowcast system framework,
the message broker,
the manager,
and the scheduler,
are managed by the `circus`_ process manager tool.

.. _circus: http://circus.readthedocs.io/en/latest/

Start the nowcast system with:

.. code-block:: bash

    $ source activate /results/nowcast-sys/nowcast-env
    (/results/nowcast-sys/nowcast-env)$ circusd --daemon $NOWCAST_CONFIG/circus.ini

:command:`circusd` monitors the long-running processes and restarts them if they crash or are shutdown accidentally.


System Management
=================

`circusctl`_ is the command-line interface for interacting with the processes that are running under :command:`circusd`.
Start it with:

.. code-block:: bash

    $ source activate /results/nowcast-sys/nowcast-env
    (/results/nowcast-sys/nowcast-env)$ circusctl --endpoint tcp://127.0.0.1:4444

.. _circusctl: http://circus.readthedocs.io/en/latest/man/circusctl/

See the `circusctl`_ man page,
or use the :kbd:`help` command within :command:`circusctl` to get information on the available commands.
A few that are useful:

* :kbd:`list` to get a comma-separated list of the processes that :command:`circusd` is managing
* :kbd:`status` to see their status
* :kbd:`stop` to stop a process;
  e.g. :kbd:`stop scheduler`
* :kbd:`start` to start a stopped process;
  e.g. :kbd:`start scheduler`
* :kbd:`restart` to stop and restart a process;
  e.g. :kbd:`restart scheduler`
* :kbd:`signal hup` to send a :kbd:`HUP` signal to a process,
  which will cause it to reload its configuration from the :envvar:`NOWCAST_YAML` file that the process was started with;
  e.g. :kbd:`signal hup manager`.
  This is the way to communicate nowcast system configuration changes to the long-running processes.
* :kbd:`quit` to stop all of the processes and shutdown :command:`circusd`

Use :kbd:`ctrl-c` to exit from :command:`circusctl`.
