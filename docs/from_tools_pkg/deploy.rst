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


*****************************
Nowcast Production Deployment
*****************************

In November 2015 the production deployment of the nowcast system was moved to the :ref:`SalishSeaModelResultsServer`, :kbd:`skookum`, in the :file:`/results/nowcast-sys/` directory tree.
This section describes the setup and operation of the nowcast system.


Mercurial Repositories
======================

Clone the following repos into :file:`/results/nowcast-sys/`:

* :ref:`tools-repo`.
* :ref:`NEMO-forcing-repo`
* :ref:`private-tools-repo`


Python Packages
===============

The Python packages that the system depends on are installed in a conda environment with:

.. code-block:: bash

    $ cd /results/nowcast-sys/
    $ conda update conda
    $ conda create --prefix /results/nowcast-sys/nowcast-env \
        bottleneck lxml mako matplotlib netCDF4 numpy pandas paramiko pillow \
        pyyaml pyzmq pip python=3 requests scipy sphinx xarray
    $ source activate /results/nowcast-sys/nowcast-env
    (/results/nowcast-sys/nowcast-env)$ pip install \
      angles arrow BeautifulSoup4 driftwood feedgen retrying sphinx-bootstrap-theme
    (/results/nowcast-sys/nowcast-env)$ cd /results/nowcast-sys/tools
    (/results/nowcast-sys/nowcast-env)$ pip install --editable SalishSeaTools/
    (/results/nowcast-sys/nowcast-env)$ pip install --editable SalishSeaCmd/
    (/results/nowcast-sys/nowcast-env)$ pip install --editable SalishSeaNowcast/


Environment Variables
=====================

Add the following files to the :file:`/results/nowcast-sys/nowcast-env` environment to automatically :command:`export` the environment variables required by the nowcast system when the environment is activated:

.. code-block:: bash

    $ cd /results/nowcast-sys/nowcast-env
    $ mkdir -p etc/conda/activate.d
    $ echo export ONC_USER_TOKEN=a_valid_ONC_data_API_user_token > etc/conda/activate.d/envvars.sh

and :command:`unset` them when it is deactivated.

.. code-block:: bash

    $ mkdir -p etc/conda/deactivate.d
    $ echo unset ONC_USER_TOKEN > etc/conda/deactivate.d/envvars.sh


Nowcast Manager Directory
=========================

The directory from which the nowcast manager runs and in which the log files and checklist file are stored is created with:

.. code-block:: bash

    $ mkdir -p $HOME/public_html/MEOPAR/nowcast/www
    $ chmod -R g+s $HOME/public_html/MEOPAR/nowcast
    $ cd $HOME/public_html/MEOPAR/nowcast
    $ ln -s /results/nowcast-sys/tools/SalishSeaNowcast/nowcast.yaml
    $ cd $HOME/public_html/MEOPAR/nowcast/www/
    $ ln -s /results/nowcast-sys/tools/SalishSeaNowcast/www/templates
    $ hg clone ssh://hg@bitbucket.org/salishsea/salishsea-site


Cold Start
==========

Start the nowcast system for the first time on a new platform with:

.. code-block:: bash

    $ touch $HOME/public_html/MEOPAR/nowcast/nowcast_checklist.yaml
    $ source activate /results/nowcast-sys/nowcast-env
    (/results/nowcast-sys/nowcast-env)$ python -m nowcast.nowcast_broker \
      $HOME/public_html/MEOPAR/nowcast/nowcast.yaml &
    (/results/nowcast-sys/nowcast-env)$ python -m nowcast.nowcast_mgr \
      $HOME/public_html/MEOPAR/nowcast/nowcast.yaml &

Exit from the shell session that the above commands were executed in to detach the borker and the manager processes from the tty.
If the shell session times out,
the broker and/or manager processes will stop.
This is,
essentially,
a hacky way of daemonizing the broker and manager processes.


Nowcast Run Directories
=======================

On the hosts where the nowcast system NEMO runs will be executed create a :file:`nowcast` directory and populate it with:

.. code-block:: bash

    $ mkdir -p NEMO-atmos open_boundaries/west/ssh rivers
    $ chmod -R g+s NEMO-atmos open_boundaries rivers
    $ ln -s ../NEMO-forcing/atmospheric/no_snow.nc
    $ ln -s ../NEMO-forcing/grid/weights-gem2.5-ops.nc
    $ ln -s ../NEMO-forcing/open_boundaries/north
    $ ln -s ../NEMO-forcing/open_boundaries/west/SalishSea2_Masson_corrected.nc
    $ ln -s ../NEMO-forcing/open_boundaries/west/tides
    $ ln -s ../NEMO-forcing/rivers/rivers_month.nc

The above :command:`ln -s` commands assume that there is a clone of the :ref:`NEMO-forcing-repo` beside the directory where the links are being created.
If the clone of the :ref:`NEMO-forcing-repo` is elsewhere,
adjust the link paths accordingly.

The hosts and their :file:`nowcast` directories presently in use are:

* :kbd:`west.cloud`
    :file:`/home/ubuntu/MEOPAR/nowcast/`

* :kbd:`ocrinus`
    :file:`/home/sallen/MEOPAR/nowcast/`

* :kbd:`salish`
    :file:`/data/dlatorne/MEOPAR/nowcast-green/`
