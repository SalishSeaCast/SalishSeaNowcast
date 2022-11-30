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


.. _SkookumSalishDeployment:

***************************************
:kbd:`skookum`/:kbd:`salish` Deployment
***************************************

Git Repositories
================

Clone the following repos into :file:`/SalishSeaCast/`:

.. code-block:: bash

    $ cd /SalishSeaCast/
    $ git clone git@github.com:SalishSeaCast/grid.git
    $ git clone git@github.com:UBC-MOAD/moad_tools.git
    $ git clone git@github.com:SalishSeaCast/NEMO-Cmd.git
    $ git clone git@github.com:43ravens/NEMO_Nowcast.git
    $ git clone git@github.com:SalishSeaCast/private-tools.git
    $ git clone git@github.com:SalishSeaCast/rivers-climatology.git
    $ git clone git@github.com:SalishSeaCast/SalishSeaCmd.git
    $ git clone git@github.com:SalishSeaCast/SalishSeaNowcast.git
    $ git clone git@github.com:SalishSeaCast/salishsea-site.git
    $ git clone git@github.com:SalishSeaCast/SS-run-sets.git
    $ git clone git@github.com:SalishSeaCast/tidal-predictions.git
    $ git clone git@github.com:SalishSeaCast/tides.git
    $ git clone git@github.com:SalishSeaCast/tools.git
    $ git clone git@github.com:SalishSeaCast/tracers.git
    $ git clone git@gitlab.com:mdunphy/FVCOM-VHFR-config.git
    $ git clone git@gitlab.com:douglatornell/OPPTools.git
    $ git clone git@github.com:SalishSeaCast/NEMO-3.6-code.git
    $ git clone git@github.com:SalishSeaCast/XIOS-ARCH.git
    $ git clone git@github.com:SalishSeaCast/XIOS-2.git

Copy the :program:`wgrib2` executable into :file:`private-tools/grib2/wgrib2/`:

.. code-block:: bash

    $ mkdir -p /SalishSeaCast/private-tools/grib2/wgrib2/
    $ cp --preserve=timestamps \
        /ocean/sallen/allen/research/MEOPAR/private-tools/grib2/wgrib2/wgrib2 \
        /SalishSeaCast/private-tools/grib2/wgrib2/


Build XIOS-2
============

Symlink the XIOS-2 build configuration files for :kbd:`salish` from the
:file:`XIOS-ARCH` repo clone into the :file:`XIOS-2/arch/` directory:

.. code-block:: bash

    $ cd /SalishSeaCast/XIOS-2/arch
    $ ln -s ../../XIOS-ARCH/UBC-EOAS/arch-GCC_SALISH.fcm
    $ ln -s ../../XIOS-ARCH/UBC-EOAS/arch-GCC_SALISH.path

:command:`ssh` to :kbd:`salish` and build XIOS-2 with:

.. code-block:: bash

    $ cd /SalishSeaCast/XIOS-2
    $ ./make_xios --arch GCC_SALISH --netcdf_lib netcdf4_seq --job 8


Build NEMO-3.6
==============

Build NEMO-3.6 and :program:`rebuild_nemo.exe`:

.. code-block:: bash

    $ cd /SalishSeaCast/NEMO-3.6-code/NEMOGCM/CONFIG
    $ XIOS_HOME=/SalishSeaCast/XIOS-2 ./makenemo -m GCC_SALISH -n SalishSeaCast_Blue -j8
    $ cd /SalishSeaCast/NEMO-3.6-code/NEMOGCM/TOOLS/
    $ XIOS_HOME=/SalishSeaCast/XIOS-2 ./maketools -m GCC_SALISH -n REBUILD_NEMO


Python Packages
===============

The Python packages that the system depends on are installed in conda environments.

.. note::
   In Mar-2022 the Python environment and package management tool used for the system
   was changed from Miniconda3 to `Mambaforge-pypy3`_.

   .. _Mambaforge-pypy3: https://github.com/conda-forge/miniforge

For the :kbd:`SalishSeaCast` automation system:

.. code-block:: bash

    $ cd /SalishSeaCast/
    $ mamba env create \
        --prefix /SalishSeaCast/nowcast-env \
        -f SalishSeaNowcast/envs/environment-prod.yaml
    $ conda activate /SalishSeaCast/nowcast-env
    (/SalishSeaCast/nowcast-env)$ python3 -m pip install --editable NEMO_Nowcast/
    (/SalishSeaCast/nowcast-env)$ python3 -m pip install --editable moad_tools/
    (/SalishSeaCast/nowcast-env)$ python3 -m pip install --editable Reshapr/
    (/SalishSeaCast/nowcast-env)$ python3 -m pip install --editable tools/SalishSeaTools/
    (/SalishSeaCast/nowcast-env)$ cd OPPTools/
    (/SalishSeaCast/nowcast-env)$ git switch SalishSeaCast-prod
    (/SalishSeaCast/nowcast-env)$ cd /SalishSeaCast/
    (/SalishSeaCast/nowcast-env)$ python3 -m pip install --editable OPPTools/
    (/SalishSeaCast/nowcast-env)$ python3 -m pip install --editable NEMO-Cmd/
    (/SalishSeaCast/nowcast-env)$ python3 -m pip install --editable SalishSeaCmd/
    (/SalishSeaCast/nowcast-env)$ python3 -m pip install --editable SalishSeaNowcast/

For the `sarracenia client`_ that maintains mirrors of the HRDPS forecast files and
rivers hydrometric files from the `ECCC MSC datamart service`_:

.. _sarracenia client: https://github.com/MetPX/sarracenia/blob/v2_stable/doc/sr_subscribe.1.rst
.. _ECCC MSC datamart service: https://dd.weather.gc.ca/

.. code-block:: bash

    $ cd /SalishSeaCast/
    $ mamba env create \
        --prefix /SalishSeaCast/sarracenia-env \
        -f SalishSeaNowcast/envs/environment-sarracenia.yaml
    $ conda activate /SalishSeaCast/sarracenia-env
    (/SalishSeaCast/sarracenia-env)$ sr_subscribe edit credentials.conf  # initialize datamart credentials

For the `salishsea-site web app`_ that is mounted at https://salishsea.eos.ubc.ca/:

.. _salishsea-site web app: https://github.com/SalishSeaCast/salishsea-site

.. code-block:: bash

    $ cd /SalishSeaCast
    $ mamba env create \
        --prefix /SalishSeaCast/salishsea-site-env \
        -f salishsea-site/envs/environment-prod.yaml
    $ conda activate /SalishSeaCast/salishsea-site-env
    (/SalishSeaCast/salishsea-site-env) $ python3 -m pip install --editable salishsea-site/


Environment Variables
=====================

:file:`/SalishSeaCast/nowcast-env`
----------------------------------

Add the following files to the :file:`/SalishSeaCast/nowcast-env` environment to
automatically :command:`export` the environment variables required by the nowcast system
when the environment is activated:

.. code-block:: bash

    $ cd /SalishSeaCast/nowcast-env
    $ mkdir -p etc/conda/activate.d
    $ cat << EOF > etc/conda/activate.d/envvars.sh
    export NOWCAST_ENV=/SalishSeaCast/nowcast-env
    export NOWCAST_CONFIG=/SalishSeaCast/SalishSeaNowcast/config
    export NOWCAST_YAML=/SalishSeaCast/SalishSeaNowcast/config/nowcast.yaml
    export NOWCAST_LOGS=/SalishSeaCast/logs/nowcast
    export NUMEXPR_MAX_THREADS=6
    export ONC_USER_TOKEN=a_valid_ONC_data_API_user_token
    export SARRACENIA_ENV=/SalishSeaCast/sarracenia-env
    export SARRACENIA_CONFIG=/SalishSeaCast/SalishSeaNowcast/sarracenia
    export SENTRY_DSN=a_valid_sentry_dsn_url
    export SLACK_SSC_DAILY_PROGRESS=a_valid_slack_incoming_webhook_url
    export SLACK_SSC_HINDCAST_PROGRESS=a_valid_slack_incoming_webhook_url
    EOF

and :command:`unset` them when it is deactivated.

.. code-block:: bash

    $ mkdir -p etc/conda/deactivate.d
    $ cat << EOF > etc/conda/deactivate.d/envvars.sh
    unset NOWCAST_ENV
    unset NOWCAST_CONFIG
    unset NOWCAST_YAML
    unset NOWCAST_LOGS
    unset NUMEXPR_MAX_THREADS
    unset ONC_USER_TOKEN
    unset SARRACENIA_ENV
    unset SARRACENIA_CONFIG
    unset SENTRY_DSN
    unset SLACK_SSC_DAILY_PROGRESS
    unset SLACK_SSC_HINDCAST_PROGRESS
    EOF


:file:`/SalishSeaCast/sarracenia-env`
-------------------------------------

The :file:`/SalishSeaCast/sarracenia-env` environment variables are included in the
:file:`SalishSeaNowcast/envs/environment-sarracenia.yaml` file so that they are managed by
:command:`conda` to automatically :command:`export` the environment variables required by the
sarracenia client when the environment is activated and :command:`unset` them when the
environment is deactivated.
To see the variables and their values:

.. code-block:: bash

    $ cd /SalishSeaCast/sarracenia-env
    $ source activate /SalishSeaCast/salishsea-site-env
    (/SalishSeaCast/salishsea-site-env) $ conda env config vars list


:file:`/SalishSeaCast/salishsea-site-env`
-----------------------------------------

Add the following files to the :file:`/SalishSeaCast/salishsea-site-env` environment to
automatically :command:`export` the environment variables required by the
https://salishsea.eos.ubc.ca website app when the environment is activated:

.. code-block:: bash

    $ cd /SalishSeaCast/salishsea-site-env
    $ mkdir -p etc/conda/activate.d
    $ cat << EOF > etc/conda/activate.d/envvars.sh
    export SALISHSEA_SITE_ENV=/SalishSeaCast/salishsea-site-env
    export SALISHSEA_SITE=/SalishSeaCast/salishsea-site
    export SALISHSEA_SITE_LOGS=/SalishSeaCast/logs/salishsea-site
    export NOWCAST_LOGS=/SalishSeaCast/logs/nowcast
    export SENTRY_DSN=a_valid_sentry_dsn_url
    EOF

and :command:`unset` them when it is deactivated.

.. code-block:: bash

    $ mkdir -p etc/conda/deactivate.d
    $ cat << EOF > etc/conda/deactivate.d/envvars.sh
    unset SALISHSEA_SITE_ENV
    unset SALISHSEA_SITE
    unset SALISHSEA_SITE_LOGS
    unset NOWCAST_LOGS
    unset SENTRY_DSN
    EOF


Nowcast Runs Directories
========================

On the hosts where the nowcast system NEMO runs will be executed create a
:file:`runs/` directory and populate it with:

.. code-block:: bash

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

* :kbd:`salish`
    :file:`/SalishSeaCast/runs/`

* :kbd:`arbutus.cloud`
    See :ref:`ArbutusCloudNEMORunsDirectory`

* :kbd:`orcinus`
    :file:`/home/sallen/MEOPAR/nowcast/`


ECCC MSC Datamart Mirror Directories
====================================

Create directories on :kbd:`skookum` for storage of the HRDPS forecast files and
rivers hydrometric files maintained by the `sarracenia client`_:

.. code-block:: bash

    $ mkdir -p /SalishSeaCast/datamart/hrdps-west
    $ mkdir -p /SalishSeaCast/datamart/hydrometric


Logging Directories
===================

Create directories on :kbd:`skookum` for storage of the nowcast system and
`salishsea-site web app`_ log files:

.. code-block:: bash

    $ mkdir -p /SalishSeaCast/logs/nowcast
    $ mkdir -p /SalishSeaCast/logs/salishsea-site


Static Web Site Assets Directories
==================================

A collection of static file assets for the `salishsea-site web app`_ are stored in the
:file:`/results/nowcast-sys/figures/` tree.
Create the that directory,
and the directories for results visualization figures from the NEMO model runs with:

.. code-block:: bash

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

.. code-block:: bash

    $ mkdir -p /results/nowcast-sys/figures/fvcom/forecast-x2
    $ mkdir -p /results/nowcast-sys/figures/fvcom/nowcast-r12
    $ mkdir -p /results/nowcast-sys/figures/fvcom/nowcast-x2

Create directories for results visualization figures from the
WaveWatch III® Strait of Georgia amd Juan de Fuca Strait wave model runs with:

.. code-block:: bash

    $ mkdir -p /results/nowcast-sys/figures/wwatch3/forecast
    $ mkdir -p /results/nowcast-sys/figures/wwatch3/forecast2

Create a directory for visualization figures generated during preparation of the
forcing files for the NEMO model runs with:

.. code-block:: bash

    $ mkdir -p /results/nowcast-sys/figures/monitoring

Create a directory for storm surge alert ATOM feed with:

.. code-block:: bash

    $ mkdir -p /results/nowcast-sys/figures/storm-surge/atom

Finally,
create a directory and symlinks for the images used on the index page of
https://salishsea.eos.ubc.ca/ with:

.. code-block:: bash

    $ mkdir -p /results/nowcast-sys/figures/salishsea-site/static/img/index_page
    $ cd /results/nowcast-sys/figures/salishsea-site/static/img/index_page
    $ ln -s /SalishSeaCast/salishsea-site/salishsea_site/static/img/index_page/about_project.svg
    $ ln -s /SalishSeaCast/salishsea-site/salishsea_site/static/img/index_page/biology.svg
    $ ln -s /SalishSeaCast/salishsea-site/salishsea_site/static/img/index_page/currents_and_physics.svg
    $ ln -s /SalishSeaCast/salishsea-site/salishsea_site/static/img/index_page/diatom_bloom_forecast.svg
    $ ln -s /SalishSeaCast/salishsea-site/salishsea_site/static/img/index_page/storm_surge_forecast.svg
    $ ln -s /SalishSeaCast/salishsea-site/salishsea_site/static/img/index_page/storm_surge_nowcast.svg

    $ mkdir -p /results/nowcast-sys/figures/bloomcast
