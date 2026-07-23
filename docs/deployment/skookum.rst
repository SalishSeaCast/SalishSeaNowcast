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


.. _SkookumDeployment:

**********************
``skookum`` Deployment
**********************

Git Repositories
================

Clone the following repos into :file:`/SalishSeaCast/`:

.. code-block:: console

    $ cd /SalishSeaCast/
    $ git clone git@github.com:SalishSeaCast/grid.git
    $ git clone git@github.com:SalishSeaCast/rivers-climatology.git
    $ git clone git@github.com:SalishSeaCast/SalishSeaNowcast.git
    $ git clone git@github.com:SalishSeaCast/salishsea-site.git
    $ git clone git@github.com:SalishSeaCast/SS-run-sets.git
    $ git clone git@github.com:SalishSeaCast/tidal-predictions.git
    $ git clone git@github.com:SalishSeaCast/tides.git
    $ git clone git@github.com:SalishSeaCast/tracers.git


Python Packages
===============

Install the `Pixi`_ environment and package manager:

.. _Pixi: https://pixi.prefix.dev/latest/

.. code-block:: console

    $ curl -fsSL https://pixi.sh/install.sh | sh

Add lines to :file:`~/.bashrc` to enable autocompletion for Pixi:

.. code-block:: console

   # Enable autocompletion for Pixi
   eval "$(pixi completion --shell bash)"

Start a new shell to apply the changes.

The Python packages that the system depends on are installed in ``default`` environment with:

.. code-block:: console

    $ cd /SalishSeaCast/SalishSeaNowcast
    $ pixi install

For the `sarracenia client`_ that maintains mirrors of the HRDPS forecast files and
rivers hydrometric files from the `ECCC MSC datamart service`_:

.. _sarracenia client: https://github.com/MetPX/sarracenia/blob/v2_dev/doc/sr_subscribe.1.rst
.. _ECCC MSC datamart service: https://dd.weather.gc.ca/

.. code-block:: console

    $ cd /SalishSeaCast/SalishSeaNowcast
    $ pixi install -e sarracenia
    $ pixi run -e sarracenia sr_subscribe edit credentials.conf  # initialize datamart credentials

For the `salishsea-site web app`_ that is mounted at https://salishsea.eos.ubc.ca/:

.. _salishsea-site web app: https://github.com/SalishSeaCast/salishsea-site

.. code-block:: console

    $ cd /SalishSeaCast/salishsea-site
    $ pixi install


Environment Variables
=====================

:file:`/SalishSeaCast/SalishSeaNowcast/.env-skookum`
----------------------------------------------------

Copy the :file:`/SalishSeaCast/SalishSeaNowcast/.env-skookum` file as
:file:`/SalishSeaCast/SalishSeaNowcast/.env` and edit it to add:

* a valid ONC data API user token as the value in the ``export ONC_USER_TOKEN=...`` line
* a valid Sentry DSN URL as the value in the ``export SENTRY_DSN=...`` line
* a valid Slack incoming webhook URL as the value in the ``export SLACK_SSC_DAILY_PROGRESS=...`` line
* a valid Slack incoming webhook URL as the value in the ``export SLACK_SSC_HINDCAST_PROGRESS=...`` line


:file:`/SalishSeaCast/sarracenia-env`
-------------------------------------

The environment variables for the ``sarracenia`` environment are included in the
``[tool.pixi.feature.sarracenia.activation.env]`` table in the
:file:`SalishSeaNowcast/pyproject.toml` file so that they are managed by Pixi to automatically
:command:`export` the environment variables required by the ``sarracenia`` client when the
a :command:`pixi run -e sarracenia ...` command is used,
or a :command:`pixi shell -e sarracenia` sub-shell is started.


:file:`/SalishSeaCast/salishsea-site/.env-template`
---------------------------------------------------

Copy the :file:`/SalishSeaCast/salishsea-site/.env-template` file as
:file:`/SalishSeaCast/salishsea-site/.env` and edit it to add:

* the token for the debug log page as the value in the ``export NOWCAST_DEBUG_LOG_TOKEN=...`` line
* a valid Sentry DSN URL as the value in the ``export SENTRY_DSN=...`` line


Nowcast Runs Directories
========================

On the hosts where the nowcast system NEMO runs will be executed create a
:file:`runs/` directory and populate it with:

.. code-block:: console

    $ chmod g+ws runs
    $ cd runs/
    $ mkdir -p LiveOcean NEMO-atmos rivers ssh
    $ chmod -R g+s LiveOcean NEMO-atmos rivers ssh
    $ cp ../SS-run-sets/v201702/nowcast-green/namelist.time_nowcast_template namelist.time
    $ ln -s ../grid
    $ ln -s ../rivers-climatology
    $ ln -s ../tides
    $ ln -s ../tracers

The hosts and their :file:`runs` directories presently in use are:

* ``arbutus.cloud``
    See :ref:`ArbutusCloudNEMORunsDirectory`

* ``orcinus``
    :file:`/home/sallen/MEOPAR/nowcast/`


ECCC MSC Datamart Mirror Directories
====================================

Create directories on ``skookum`` for storage of the HRDPS forecast files and
rivers hydrometric files maintained by the `sarracenia client`_:

.. code-block:: console

    $ mkdir -p /SalishSeaCast/datamart/hrdps-west
    $ mkdir -p /SalishSeaCast/datamart/hydrometric


Logging Directories
===================

Create directories on ``skookum`` for storage of the nowcast system and
`salishsea-site web app`_ log files:

.. code-block:: console

    $ mkdir -p /SalishSeaCast/logs/nowcast
    $ mkdir -p /SalishSeaCast/logs/salishsea-site


Static Web Site Assets Directories
==================================

A collection of static file assets for the `salishsea-site web app`_ are stored in the
:file:`/results/nowcast-sys/figures/` tree.
Create the that directory,
and the directories for results visualization figures from the NEMO model runs with:

.. code-block:: console

    $ mkdir -p /results/nowcast-sys/figures
    $ chmod g+ws /results/nowcast-sys/figures
    $ mkdir -p /results/nowcast-sys/figures/forecast
    $ mkdir -p /results/nowcast-sys/figures/forecast2
    $ mkdir -p /results/nowcast-sys/figures/nowcast
    $ mkdir -p /results/nowcast-sys/figures/nowcast-agrif
    $ mkdir -p /results/nowcast-sys/figures/nowcast-green
    $ mkdir -p /results/nowcast-sys/figures/surface_currents/forecast
    $ mkdir -p /results/nowcast-sys/figures/surface_currents/forecast2

Create directories for results visualization figures from the
FVCOM Vancouver Harbour and Lower Fraser River model runs with:

.. code-block:: console

    $ mkdir -p /results/nowcast-sys/figures/fvcom/forecast-x2
    $ mkdir -p /results/nowcast-sys/figures/fvcom/nowcast-r12
    $ mkdir -p /results/nowcast-sys/figures/fvcom/nowcast-x2

Create directories for results visualization figures from the
WaveWatch III® Strait of Georgia amd Juan de Fuca Strait wave model runs with:

.. code-block:: console

    $ mkdir -p /results/nowcast-sys/figures/wwatch3/forecast
    $ mkdir -p /results/nowcast-sys/figures/wwatch3/forecast2

Create a directory for visualization figures generated during preparation of the
forcing files for the NEMO model runs with:

.. code-block:: console

    $ mkdir -p /results/nowcast-sys/figures/monitoring

Create a directory for storm surge alert ATOM feed with:

.. code-block:: console

    $ mkdir -p /results/nowcast-sys/figures/storm-surge/atom

Finally,
create a directory and symlinks for the images used on the index page of
https://salishsea.eos.ubc.ca/ with:

.. code-block:: console

    $ mkdir -p /results/nowcast-sys/figures/salishsea-site/static/img/index_page
    $ cd /results/nowcast-sys/figures/salishsea-site/static/img/index_page
    $ ln -s /SalishSeaCast/salishsea-site/salishsea_site/static/img/index_page/about_project.svg
    $ ln -s /SalishSeaCast/salishsea-site/salishsea_site/static/img/index_page/biology.svg
    $ ln -s /SalishSeaCast/salishsea-site/salishsea_site/static/img/index_page/currents_and_physics.svg
    $ ln -s /SalishSeaCast/salishsea-site/salishsea_site/static/img/index_page/diatom_bloom_forecast.svg
    $ ln -s /SalishSeaCast/salishsea-site/salishsea_site/static/img/index_page/storm_surge_forecast.svg
    $ ln -s /SalishSeaCast/salishsea-site/salishsea_site/static/img/index_page/storm_surge_nowcast.svg

    $ mkdir -p /results/nowcast-sys/figures/bloomcast


Persistent Dask Cluster for :py:mod:`~nowcast.workers.make_averaged_dataset` Worker
===================================================================================

The :py:mod:`~nowcast.workers.make_averaged_dataset` worker is launched:

* after every nowcast-green run to down-sample hour-average NEMO results files to day-averaged files
* after that processing is completed at the end of each month to down-sample day-averaged files
  to month-averaged files

That means that there are often concurrent instances of the worker.
Instead of letting each worker instance spin up its own *ad hoc* dask cluster,
we use a persistent dask cluster on ``salish`` that the worker dispatches tasks to.

Create a :program:`tmux` session on ``salish`` for the dask cluster:

.. code-block:: console

    $ tmux new -s make_averaged_dataset

In the first :program:`tmux` terminal,
launch the :command:`dask-scheduler` with its serving port on 4386,
and its dashboard port on 4387:

.. code-block:: console

    $ cd /SalishSeaCast/SalishSeaNowcast
    $ pixi run dask scheduler --port 4386 --dashboard-address :4387

Use :kbd:`Control-b ,` to rename the :program:`tmux` terminal to ``dask-scheduler``.

Start a second :program:`tmux` terminal with :kbd:`Control-b c`,
launch the 4 :command:`dask worker` processes with these properties:

* 1 thread per worker
* 64G memory limit per worker
* worker files stored on the :file:`/tmp/SalishSeaCast/` directory
* workers restart every 3600 seconds with 60 second random staggering of their restart times
* workers communicate with the scheduler on port 4386

.. code-block:: console

    $ cd /SalishSeaCast/SalishSeaNowcast
    $ pixi run dask worker --nworkers=4 --nthreads=1 --memory-limit 64G \
        --local-directory /tmp/SalishSeaCast \
        --lifetime 3600 --lifetime-stagger 60 --lifetime-restart \
        localhost:4386

Use :kbd:`Control-b ,` to rename the :program:`tmux` terminal to ``dask-workers``.



``ssh`` Keys and Configuration
==============================

Generate a passphrase-less RSA key pair to use for connections to most remote hosts:

.. code-block:: console

    $ ssh-keygen -t rsa -f $HOME/.ssh/SalishSeaNEMO-nowcast_id_rsa -C SalishSeaNEMO-nowcast

Use :command:`ssh-copy-id` to install the public key on ``arbutus``,
``optimum``,
and ``orcinus``;
e.g.

.. code-block:: console

    $ ssh-copy-id -i $HOME/.ssh/SalishSeaNEMO-nowcast_id_rsa arbutus.cloud

Generate a passphrase-less ED25519 key pair to use for connections to the ``nibi`` HPC cluster:

.. code-block:: console

    $ ssh-keygen -t ed25519 -f $HOME/.ssh/SalishSeaCast_robot.nibi_ed25519 -C "SalishSeaCast robot.nibi"

Edit the public key to prefix it with the constraint predicates necessary for automation in the
context of multuifactor authentication on the ``nibi`` cluster.
The constraint predicates are:

.. code-block:: text

    restrict,from="142.103.36.*",command="/cvmfs/soft.computecanada.ca/custom/bin/computecanada/allowed_commands/transfer_commands.sh"

Use https://ccdb.computecanada.ca/ssh_authorized_keys to install the public key for ``nibi`` via
the Alliance CCDB.

Add the following stanzas to :file:`$HOME/.ssh/config` on ``skookum``:

.. code-block:: text

    Host arbutus.cloud-nowcast
        HostName        <ip-address>
        User            ubuntu
        IdentityFile    ~/.ssh/SalishSeaNEMO-nowcast_id_rsa
        ForwardAgent    no

    Host robot.nibi
        HostName     robot.nibi.alliancecan.ca
        User         <userid>
        IdentityFile    ~/.ssh/SalishSeaCast_robot.nibi_ed25519
        ForwardAgent no

    Host optimum-hindcast
        HostName optimum.eos.ubc.ca
        User <userid>
        HostKeyAlgorithms=+ssh-rsa
        PubkeyAcceptedKeyTypes=+ssh-rsa
        IdentityFile    ~/.ssh/SalishSeaNEMO-nowcast_id_rsa
        ForwardAgent no

    Host orcinus-nowcast-agrif
        HostName     orcinus.westgrid.ca
        User         <userid>
        HostKeyAlgorithms=+ssh-rsa
        PubkeyAcceptedKeyTypes=+ssh-rsa
        IdentityFile    ~/.ssh/SalishSeaNEMO-nowcast_id_rsa
        ForwardAgent no
