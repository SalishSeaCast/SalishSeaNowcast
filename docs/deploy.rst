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


.. _NowcastProductionDeployment:

*****************************
Nowcast Production Deployment
*****************************

In October 2016 the production deployment of the nowcast system was changed to use the `SalishSeaNowcast`_ package that is based on the `NEMO_Nowcast framework`_ framework.
The deployment remains on the :ref:`SalishSeaModelResultsServer`, :kbd:`skookum`, in the :file:`/results/nowcast-sys/` directory tree.

.. _NEMO_Nowcast framework: http://nemo-nowcast.readthedocs.io/en/latest/
.. _SalishSeaNowcast: https://bitbucket.org/salishsea/salishseanowcast

This section describes the setup and operation of the nowcast system.


Mercurial Repositories
======================

Clone the following repos into :file:`/results/nowcast-sys/`:

* `NEMO_Nowcast`_
* `SalishSeaNowcast`_
* :ref:`tools-repo`
* :ref:`private-tools-repo`
* :ref:`NEMO-forcing-repo`
* :ref:`NEMO-3.6-code-repo`
* :ref:`XIOS-repo`
* :ref:`salishsea-site-repo`


.. _NEMO_Nowcast: https://bitbucket.org/43ravens/nemo_nowcast

Copy the :program:`wgrib2` executable into :file:`private-tools/grib2/wgrib2/`:

.. code-block:: bash

    $ cp --preserve=timestamps \
        /ocean/sallen/allen/research/MEOPAR/private-tools/grib2/wgrib2/wgrib2 \
        /results/nowcast-sys/private-tools/grib2/wgrib2/


Build XIOS
==========

.. TODO::
    Write this section.


Build NEMO-3.6
==============

.. TODO::
    Write this section.


Python Packages
===============

The Python packages that the system depends on are installed in a conda environment with:

.. code-block:: bash

    $ cd /results/nowcast-sys/
    $ conda update conda
    $ conda create \
        --prefix /results/nowcast-sys/nemo_nowcast-env \
        --channel gomss-nowcast --channel defaults --channel conda-forge \
        arrow attrs beautifulsoup4 bottleneck circus cliff matplotlib netcdf4 \
        numpy pandas paramiko pip python=3 pyyaml pyzmq retrying requests \
        schedule scipy xarray
    $ source activate /results/nowcast-sys/nemo_nowcast-env
    (/results/nowcast-sys/nemo_nowcast-env)$ pip install angles driftwood raven
    (/results/nowcast-sys/nemo_nowcast-env)$ cd /results/nowcast-sys/
    (/results/nowcast-sys/nemo_nowcast-env)$ pip install --editable NEMO_Nowcast/
    (/results/nowcast-sys/nemo_nowcast-env)$ pip install --editable tools/SalishSeaTools/
    (/results/nowcast-sys/nemo_nowcast-env)$ pip install --editable tools/SalishSeaCmd/
    (/results/nowcast-sys/nemo_nowcast-env)$ pip install --editable SalishSeaNowcast/


Environment Variables
=====================

Add the following files to the :file:`/results/nowcast-sys/nowcast-env` environment to automatically :command:`export` the environment variables required by the nowcast system when the environment is activated:

.. code-block:: bash

    $ cd /results/nowcast-sys/nemo_nowcast-env
    $ mkdir -p etc/conda/activate.d
    $ cat << EOF > etc/conda/activate.d/envvars.sh
    export NOWCAST_ENV=/results/nowcast-sys/nemo_nowcast-env
    export NOWCAST_CONFIG=/results/nowcast-sys/SalishSeaNowcast/config
    export NOWCAST_YAML=/results/nowcast-sys/SalishSeaNowcast/config/nowcast.yaml
    export NOWCAST_LOGS=/results/nowcast-sys/logs/nowcast
    export ONC_USER_TOKEN=a_valid_ONC_data_API_user_token
    export SENTRY_DSN=a_valid_sentry_dsn_url
    EOF

and :command:`unset` them when it is deactivated.

.. code-block:: bash

    $ mkdir -p etc/conda/deactivate.d
    $ cat << EOF > etc/conda/deactivate.d/envvars.sh
    unset NOWCAST_ENV
    unset NOWCAST_CONFIG
    unset NOWCAST_YAML
    unset NOWCAST_LOGS
    unset ONC_USER_TOKEN
    unset SENTRY_DSN
    EOF


Nowcast Runs Directories
========================

On the hosts where the nowcast system NEMO runs will be executed create a :file:`runs` directory and populate it with:

.. code-block:: bash

    $ chmod g+ws runs
    $ cd runs/
    $ mkdir -p NEMO-atmos open_boundaries/west/ssh rivers
    $ chmod -R g+s NEMO-atmos open_boundaries rivers
    $ ln -s ../../NEMO-forcing/atmospheric/no_snow.nc NEMO-atmos/
    $ ln -s ../../NEMO-forcing/grid/weights-gem2.5-ops.nc NEMO-atmos/
    $ ln -s ../../NEMO-forcing/open_boundaries/north open_boundaries/
    $ ln -s ../../../NEMO-forcing/open_boundaries/west/SalishSea2_Masson_corrected.nc open_boundaries/west/
    $ ln -s ../../../NEMO-forcing/open_boundaries/west/SalishSea_west_TEOS10.nc open_boundaries/west/
    $ ln -s ../../../NEMO-forcing/open_boundaries/west/tides open_boundaries/west/
    $ ln -s ../../NEMO-forcing/rivers/bio_climatology rivers/
    $ ln -s ../../NEMO-forcing/rivers/river_ConsTemp_month.nc rivers/
    $ ln -s ../../NEMO-forcing/rivers/rivers_month.nc rivers/
    $ cp ../SS-run-sets/SalishSea/nemo3.6/nowcast/namelist.time_nowcast_template namelist.time
    $ ln -s ../SS-run-sets/SalishSea/nemo3.6/nowcast/namelist.surface.blue namelist.surface
    $ ln -sf ../SS-run-sets/SalishSea/nemo3.6/nowcast/iodef_blue_cloud.xml iodef.xml

The above :command:`ln -s` commands assume that there is a clone of the :ref:`NEMO-forcing-repo` beside the directory where the links are being created.
If the clone of the :ref:`NEMO-forcing-repo` is elsewhere,
adjust the link paths accordingly.

The hosts and their :file:`runs` directories presently in use are:

* :kbd:`west.cloud`
    :file:`/home/ubuntu/MEOPAR/nowcast-sys/runs/`

* :kbd:`orcinus`
    :file:`/home/sallen/MEOPAR/nowcast/`

* :kbd:`salish`
    :file:`/results/nowcast-sys/runs/`


Static Web Pages Directory
==========================

.. TODO::
    This is fuzzy until the web page builder workers are ported.
    Progress on the salish sea site Pyramid app also plays a roll in this.

.. code-block:: bash

    $ mkdir -p $HOME/public_html/MEOPAR/nowcast/www
    $ chmod -R g+s $HOME/public_html/MEOPAR/nowcast
    $ cd $HOME/public_html/MEOPAR/nowcast
    $ ln -s /results/nowcast-sys/tools/SalishSeaNowcast/nowcast.yaml
    $ cd $HOME/public_html/MEOPAR/nowcast/www/
    $ ln -s /results/nowcast-sys/tools/SalishSeaNowcast/www/templates
    $ hg clone ssh://hg@bitbucket.org/salishsea/salishsea-site


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

    $ source activate /results/nowcast-sys/nemo_nowcast-env
    (/results/nowcast-sys/nemo_nowcast-env)$ circusd --daemon $NOWCAST_CONFIG/circus.ini

:command:`circusd` monitors the long-running processes and restarts them if they crash or are shutdown accidentally.


System Management
=================

`circusctl`_ is the command-line interface for interacting with the processes that are running under :command:`circusd`.
Start it with:

.. code-block:: bash

    $ source activate /results/nowcast-sys/nemo_nowcast-env
    (/results/nowcast-sys/nemo_nowcast-env)$ circusctl --endpoint tcp:127.0.0.1:4444

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
* :kbd:`signal hup` to send a :kbd:`HUP` signnal to a process,
  which will cause it to reload its configuration from the :envvar:`NOWCAST_YAML` file that the process was started with;
  e.g. :kbd:`signal hup manager`.
  This is the way to communicate nowcast system configuration changes to the long-running processes.
* :kbd:`quit` to stop all of the processes and shutdown :command:`circusd`

Use :kbd:`ctrl-c` to exit from :command:`circusctl`.
