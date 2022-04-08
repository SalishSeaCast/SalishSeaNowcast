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
the log aggregator,
the message broker,
and the manager,
are managed by the `supervisor`_ process manager tool.
So is the `sarracenia client`_ that maintains mirrors of the HRDPS forecast files and rivers hydrometric files from the `ECCC MSC datamart service`_.

.. _supervisor: http://supervisord.org/
.. _sarracenia client: https://github.com/MetPX/sarracenia/blob/v2_stable/doc/sr_subscribe.1.rst
.. _ECCC MSC datamart service: https://dd.weather.gc.ca/


Start the nowcast system and sarracenia client with:

.. code-block:: bash

    $ source activate /results/nowcast-sys/nowcast-env
    (/results/nowcast-sys/nowcast-env)$ supervisord --configuration $NOWCAST_CONFIG/supervisord.ini

:command:`supervisord` monitors the long-running processes and restarts them if they crash or are shutdown accidentally.

The https://salishsea.eos.ubc.ca website app is also managed by `supervisor`_.
Start it with:

.. code-block:: bash

    $ source activate /SalishSeaCast/salishsea-site-env
    (/SalishSeaCast/salishsea-site-env)$ supervisord --configuration $SALISHSEA_SITE/supervisord-prod.ini


System Management
=================

`supervisorctl`_ is the command-line interface for interacting with the processes that are running under :command:`supervisord`.
Start it with:

.. code-block:: bash

    $ source activate /results/nowcast-sys/nowcast-env
    (/results/nowcast-sys/nowcast-env)$ supervisorctl --configuration $NOWCAST_CONFIG/supervisord.ini

.. _supervisorctl: http://supervisord.org/running.html#running-supervisorctl

See the `supervisorctl`_ docs,
or use the :kbd:`help` command within :command:`supervisorctl` to get information on the available commands.
A few that are useful:

* :kbd:`avail` to get a list of the processes that :command:`supervisord` is configured to manage
* :kbd:`status` to see their status
* :kbd:`stop` to stop a process;
  e.g. :kbd:`stop manager`
* :kbd:`start` to start a stopped process;
  e.g. :kbd:`start manager`
* :kbd:`restart` to stop and restart a process;
  e.g. :kbd:`restart manager`
* :kbd:`signal hup` to send a :kbd:`HUP` signal to a process,
  which will cause it to reload its configuration from the :envvar:`NOWCAST_YAML` file that the process was started with;
  e.g. :kbd:`signal hup manager`.
  This is the way to communicate nowcast system configuration changes to the long-running processes.
* :kbd:`shutdown` to stop all of the processes and shutdown :command:`supervisord`

Use :kbd:`quit` or :kbd:`exit` to exit from :command:`supervisorctl`.

`sr_subscribe`_ is the command-line interface for interacting with the `sarracenia client`_ that maintains mirrors of the HRDPS forecast files and rivers hydrometric files from the `ECCC MSC datamart service`_.

.. _sr_subscribe: https://github.com/MetPX/sarracenia/blob/v2_stable/doc/sr_subscribe.1.rst

:command:`sr_subscribe` is run in :kbd:`foreground` mode instead of daemonized so that it can be managed by ::command:`supervisord`.
Use :command:`supervisorctl` to view the :command:`sr_subscribe` log files:\

.. code-block:: bash

    $ source activate /results/nowcast-sys/nowcast-env
    (/results/nowcast-sys/nowcast-env)$ supervisorctl --configuration $NOWCAST_CONFIG/supervisord.ini tail sr_subscribe-hrdps-west

or

.. code-block:: bash

    (/results/nowcast-sys/nowcast-env)$ supervisorctl --configuration $NOWCAST_CONFIG/supervisord.ini tail sr_subscribe-hydrometric

Use :command:`tail -f` to follow the logs to view updates as they occur.


Automatic Deployment of Changes to :kbd:`salishsea-site` App
============================================================

A `GitHub Actions workflow`_ causes changes to be pulled and updated to :file:`/SalishSeaCast/salishsea-site/` and the app to be restarted via :command:`supervisorctl` whenever changes are pushed to the repo on GitHub.

.. _GitHub Actions workflow: https://github.com/SalishSeaCast/salishsea-site/actions?query=workflow:deployment
