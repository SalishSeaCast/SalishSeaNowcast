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

.. _SkookumSalishDeployment:

***************************************
:kbd:`skookum`/:kbd:`salish` Deployment
***************************************

Mercurial Repositories
======================

Clone the following repos into :file:`/SalishSeaCast/`:

.. code-block:: bash

    $ cd /SalishSeaCast/
    $ hg clone ssh://hg@bitbucket.org/salishsea/grid grid
    $ hg clone ssh://hg@bitbucket.org/UBC_MOAD/moad_tools moad_tools
    $ hg clone ssh://hg@bitbucket.org/salishsea/nemo-3.6-code NEMO-3.6-code
    $ hg clone ssh://hg@bitbucket.org/salishsea/nemo-cmd NEMO-Cmd
    $ hg clone ssh://hg@bitbucket.org/43ravens/nemo_nowcast NEMO_Nowcast
    $ hg clone ssh://hg@bitbucket.org/salishsea/private-tools private-tools
    $ hg clone ssh://hg@bitbucket.org/salishsea/rivers-climatology rivers-climatology
    $ hg clone ssh://hg@bitbucket.org/salishsea/salishseacmd SalishSeaCmd
    $ hg clone ssh://hg@bitbucket.org/salishsea/salishseanowcast SalishSeaNowcast
    $ hg clone ssh://hg@bitbucket.org/salishsea/salishsea-site salishsea-site
    $ hg clone ssh://hg@bitbucket.org/salishsea/ss-run-sets SS-run-sets
    $ hg clone ssh://hg@bitbucket.org/salishsea/tides tides
    $ hg clone ssh://hg@bitbucket.org/salishsea/tools tools
    $ hg clone ssh://hg@bitbucket.org/salishsea/tracers tracers
    $ hg clone ssh://hg@bitbucket.org/salishsea/xios-2 XIOS-2
    $ hg clone ssh://hg@bitbucket.org/salishsea/xios-arch XIOS-ARCH

Copy the :program:`wgrib2` executable into :file:`private-tools/grib2/wgrib2/`:

.. code-block:: bash

    $ mkdir -p /SalishSeaCast/private-tools/grib2/wgrib2/
    $ cp --preserve=timestamps \
        /ocean/sallen/allen/research/MEOPAR/private-tools/grib2/wgrib2/wgrib2 \
        /SalishSeaCast/private-tools/grib2/wgrib2/


Git Repositories
================

Clone the following repos into :file:`/SalishSeaCast/`:

.. code-block:: bash

    $ cd /SalishSeaCast/
    $ git clone git@gitlab.com:mdunphy/FVCOM-VHFR-config.git
    $ git clone git@gitlab.com:mdunphy/OPPTools.git OPPTools


Build XIOS-2
============

Symlink the XIOS-2 build configuration files for :kbd:`salish` from the :file:`XIOS-ARCH` repo clone into the :file:`XIOS-2/arch/` directory:

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

    $ cd /SalishSeaCast/nowcast-sys/NEMO-3.6-code/NEMOGCM/CONFIG
    $ XIOS_HOME=/SalishSeaCast/XIOS-2 ./makenemo -m GCC_SALISH -n SalishSeaCast -j8
    $ cd /SalishSeaCast/nowcast-sys/NEMO-3.6-code/NEMOGCM/TOOLS/
    $ XIOS_HOME=/SalishSeaCast/XIOS-2 ./maketools -m GCC_SALISH -n REBUILD_NEMO


Python Packages
===============

The Python packages that the system depends on are installed in conda environments.

For the :kbd:`SalishSeaCast` automation system:

.. code-block:: bash

    $ cd /SalishSeaCast/
    $ conda update conda
    $ conda create \
        --prefix /SalishSeaCast/nowcast-env \
        --channel conda-forge --channel defaults --channel gomss-nowcast \
        arrow attrs basemap beautifulsoup4 bottleneck circus cliff cmocean \
        dask docutils gsw lxml mako matplotlib=1.5.3 netcdf4 numpy pandas paramiko \
        pillow pip poppler pygrib pypdf2 pyproj python=3.6 pyyaml pyzmq \
        requests scipy shapely watchdog xarray
    $ source activate /SalishSeaCast/nowcast-env
    (/SalishSeaCast/nowcast-env)$ pip install angles driftwood \
        f90nml feedgen python-hglib raven retrying schedule scour tables utm zeep
    (/SalishSeaCast/nowcast-env)$ pip install --editable NEMO_Nowcast/
    (/SalishSeaCast/nowcast-env)$ pip install --editable moad_tools/
    (/SalishSeaCast/nowcast-env)$ pip install --editable tools/SalishSeaTools/
    (/SalishSeaCast/nowcast-env)$ pip install --editable OPPTools/
    (/SalishSeaCast/nowcast-env)$ pip install --editable NEMO-Cmd/
    (/SalishSeaCast/nowcast-env)$ pip install --editable SalishSeaCmd/
    (/SalishSeaCast/nowcast-env)$ pip install --editable SalishSeaNowcast/

For the `sarracenia client`_ that maintains mirrors of the HRDPS forecast files and rivers hydrometric files from the `ECCC MSC datamart service`_:

.. _sarracenia client: https://github.com/MetPX/sarracenia/blob/master/doc/sr_subscribe.1.rst#documentation
.. _ECCC MSC datamart service: https://dd.weather.gc.ca/

.. code-block:: bash

    $ cd /SalishSeaCast/
    $ conda update conda
    $ conda create \
        --prefix /SalishSeaCast/sarracenia-env \
        --channel conda-forge \
        python=3 appdirs watchdog netifaces humanize psutil paramiko
    $ source activate /SalishSeaCast/sarracenia-env
    (/SalishSeaCast/sarracenia-env)$ pip install amqplib metpx-sarracenia
    (/SalishSeaCast/sarracenia-env)$ sr_subscribe edit credentials.conf  # initialize datamart credentials

For the `salishsea-site web app`_ that is mounted at https://salishsea.eos.ubc.ca/:

.. _salishsea-site web app: https://bitbucket.org/salishsea/salishsea-site

.. code-block:: bash

    $ cd /SalishSeaCast
    $ conda update conda
    $ conda create \
        --prefix /SalishSeaCast/salishsea-site-env \
        --channel conda-forge \
        python=3 pyyaml requests "pyzmq<17.0,>=13.1.0"
    $ source activate /SalishSeaCast/salishsea-site-env
    (/SalishSeaCast/salishsea-site-env) $ pip install \
        arrow attrs chaussette circus pyramid pyramid_crow pyramid_mako \
        "waitress==0.9.0"
    (/SalishSeaCast/salishsea-site-env) $ pip install --editable salishsea-site/


Environment Variables
=====================

Add the following files to the :file:`/SalishSeaCast/nowcast-env` environment to automatically :command:`export` the environment variables required by the nowcast system when the environment is activated:

.. code-block:: bash

    $ cd /SalishSeaCast/nowcast-env
    $ mkdir -p etc/conda/activate.d
    $ cat << EOF > etc/conda/activate.d/envvars.sh
    export NOWCAST_ENV=/SalishSeaCast/nowcast-env
    export NOWCAST_CONFIG=/SalishSeaCast/SalishSeaNowcast/config
    export NOWCAST_YAML=/SalishSeaCast/SalishSeaNowcast/config/nowcast.yaml
    export NOWCAST_LOGS=/SalishSeaCast/logs/nowcast
    export ONC_USER_TOKEN=a_valid_ONC_data_API_user_token
    export SARRACENIA_ENV=/SalishSeaCast/sarracenia-env
    export SARRACENIA_CONFIG=/SalishSeaCast/SalishSeaNowcast/sarracenia
    export SENTRY_DSN=a_valid_sentry_dsn_url
    export SLACK_SSC_DAILY_PROGRESS=a_valid_slack_incoming_webhook_url
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
    unset SARRCENIA_ENV
    unset SARRACENIA_CONFIG
    unset SENTRY_DSN
    unset SLACK_SSC_DAILY_PROGRESS
    EOF

Add the following files to the :file:`/SalishSeaCast/sarracenia-env` environment to automatically :command:`export` the environment variables required by the sarracenia client when the environment is activated:

.. code-block:: bash

    $ cd /SalishSeaCast/sarracenia-env
    $ mkdir -p etc/conda/activate.d
    $ cat << EOF > etc/conda/activate.d/envvars.sh
    export SARRACENIA_ENV=/SalishSeaCast/sarracenia-env
    export SARRACENIA_CONFIG=/SalishSeaCast/SalishSeaNowcast/sarracenia
    export SENTRY_DSN=a_valid_sentry_dsn_url
    EOF

and :command:`unset` them when it is deactivated.

.. code-block:: bash

    $ mkdir -p etc/conda/deactivate.d
    $ cat << EOF > etc/conda/deactivate.d/envvars.sh
    unset SARRCENIA_ENV
    unset SARRACENIA_CONFIG
    unset SENTRY_DSN
    EOF

Add the following files to the :file:`/SalishSeaCast/salishsea-site-env` environment to automatically :command:`export` the environment variables required by the https://salishsea.eos.ubc.ca website app when the environment is activated:

.. code-block:: bash

    $ cd /SalishSeaCast/salishsea-site-env
    $ mkdir -p etc/conda/activate.d
    $ cat << EOF > etc/conda/activate.d/envvars.sh
    export SALISHSEA_SITE_ENV=/SalishSeaCast/salishsea-site-env
    export SALISHSEA_SITE=/SalishSeaCast/salishsea-site
    export NOWCAST_LOGS=/SalishSeaCast/logs/nowcast
    export SENTRY_DSN=a_valid_sentry_dsn_url
    EOF

and :command:`unset` them when it is deactivated.

.. code-block:: bash

    $ mkdir -p etc/conda/deactivate.d
    $ cat << EOF > etc/conda/deactivate.d/envvars.sh
    unset SALISHSEA_SITE_ENV
    unset SALISHSEA_SITE
    unset NOWCAST_LOGS
    unset SENTRY_DSN
    EOF


Nowcast Runs Directories
========================

On the hosts where the nowcast system NEMO runs will be executed create a :file:`runs/` directory and populate it with:

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

* :kbd:`west.cloud`
    See :ref:`WestCloudNowcastRunsDirectory`

* :kbd:`orcinus`
    :file:`/home/sallen/MEOPAR/nowcast/`


ECCC MSC Datamart Mirror Directories
====================================

Create directories on :kbd:`skookum` for storage of the HRDPS forecast files and rivers hydrometric files maintained by the `sarracenia client`_:

.. code-block:: bash

    $ mkdir -p /SalishSeaCast/datamart/hrdps-west
    $ mkdir -p /SalishSeaCast/datamart/hydrometric


Static Web Pages Directory
==========================

.. TODO::
    This is fuzzy until the web page builder workers are ported.
    Progress on the salish sea site Pyramid app also plays a roll in this.

.. code-block:: bash

    $ mkdir -p $HOME/public_html/MEOPAR/nowcast/www
    $ chmod -R g+s $HOME/public_html/MEOPAR/nowcast
    $ cd $HOME/public_html/MEOPAR/nowcast
    $ ln -s /SalishSeaCast/tools/SalishSeaNowcast/nowcast.yaml
    $ cd $HOME/public_html/MEOPAR/nowcast/www/
    $ ln -s /SalishSeaCast/tools/SalishSeaNowcast/www/templates
    $ hg clone ssh://hg@bitbucket.org/salishsea/salishsea-site
