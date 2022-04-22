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

.. _OptimumDeployment:

*******************************************
:kbd:`optimum` Deployment for Hindcast Runs
*******************************************

Doug maintains the production deployment on :kbd:`optimum` in the group :kbd:`sallen` directory trees.
That means that,
for the purposes of these docs,
the value of :envvar:`HOME` is :file:`/home/sallen/dlatorne`.


Environment Variables
=====================

Add these environment variable definitions to :file:`$HOME/.bash_profile`::

  export FORCING=/data/sallen/shared
  export PROJECT=/home/sallen/dlatorne

:kbd:`optimum` provides automatically defined environment variables for:

  :envvar:`ARCHIVEDIR`
    for storing semi-permanent input and results. (no backup)
    DO NOT USE for applications, setups, and scripts.
    !!! file lifetime of 3 years based on recent-access time
  :envvar:`SCRATCHDIR`
    for working/running jobs; routinely cleaned up (no backup)
    DO NOT USE for applications, setups, and scripts.
    !!! file lifetime of 1 year based on recent-access time


Module Loads
============

The default module loads to use on :kbd:`optimum` are::

  module load OpenMPI/2.1.6/GCC/SYSTEM
  module load GIT/2/03.03

Loading of those modules is included in :file:`$HOME/.bashrc`.

There is a :kbd:`Miniconda/3` module available for building Python Conda environments.
Conda environments created with that module loaded are stored in :file:`$HOME/.conda/envs/`.

There is something funky about :program:`REBUILD_NEMO` and the way it uses netCDF that requires a different collection of modules in order to avoid a run-time error about netCDF4 operations on netCDF3 files
(or vice versa)::

  module load GCC/8.3
  module load OpenMPI/2.1.6/GCC/8.3
  module load ZLIB/1.2/11
  module load use.paustin
  module load HDF5/1.08/20
  module load NETCDF/4.6/1

.. warning::
    The above module loads can *only be used* for build and execution of :program:`REBUILD_NEMO`.
    Bad things will happen if XIOS or NEMO are built with those modules loaded.

    :command:`salishsea run` takes care of switching the modules loads between running :program:`nemo.exe` and :program:`REBUILD_NEMO`,
    but you will need to manually load the above modules if you need to manually run :command:`salishsea combine` for some reason.


Create Directory Trees
======================

Create directory trees for the run preparation directory,
Git repositories,
and temporary run directories:

.. code-block:: bash

    $ mkdir -p $PROJECT/SalishSeaCast/hindcast-sys/runs

Store results directories in a tree in :envvar:`SCRATCHDIR`,
for example:

.. code-block:: bash

    $ mkdir -p #SCRATCHDIR/hindcast.201905/
    $ chmod g+ws #SCRATCHDIR/hindcast.201905/


Clone Git Repositories
======================

Clone the following repos into :file:`$PROJECT/SalishSeaCast/hindcast-sys/`:

.. code-block:: bash

    $ cd $PROJECT/SalishSeaCast/hindcast-sys/
    $ git clone git@github.com:SalishSeaCast/grid.git
    $ git clone git@github.com:SalishSeaCast/NEMO-3.6-code.git
    $ git clone git@github.com:SalishSeaCast/NEMO-Cmd.git
    $ git clone git@github.com:SalishSeaCast/rivers-climatology.git
    $ git clone git@github.com:SalishSeaCast/SalishSeaCmd.git
    $ git clone git@github.com:SalishSeaCast/sea_initial.git
    $ git clone git@github.com:SalishSeaCast/SS-run-sets.git
    $ git clone git@github.com:SalishSeaCast/tides.git
    $ git clone git@github.com:SalishSeaCast/tracers.git
    $ git clone git@github.com:SalishSeaCast/XIOS-ARCH.git
    $ git clone git@github.com:SalishSeaCast/XIOS-2.git


Build XIOS-2
============

Symlink the XIOS-2 build configuration files for :kbd:`optimum` from the :file:`XIOS-ARCH` repo clone into the :file:`XIOS-2/arch/` directory:

.. code-block:: bash

    $ cd $PROJECT/SalishSeaCast/hindcast-sys/XIOS-2/arch
    $ ln -s ../../XIOS-ARCH/UBC-EOAS/arch-GCC_OPTIMUM.env
    $ ln -s ../../XIOS-ARCH/UBC-EOAS/arch-GCC_OPTIMUM.fcm
    $ ln -s ../../XIOS-ARCH/UBC-EOAS/arch-GCC_OPTIMUM.path

Despite many attempts with various combinations of compilers,
OpenMPI library versions,
and netCDF library versions,
the only way found to successfully build XIOS-2 is with the :kbd:`OpenMPI/2.1.6/GCC/SYSTEM` module.
That forces us to use the SVN :kbd:`r1066` checkout version of XIOS-2.
That version is pointed to by both the :kbd:`XIOS-2r1066` and the :kbd:`PROD-hindcast_201905-v3`
(and later :kbd:`PROD-hindcast_*`)
Git tags,
so create a branch to checkout the repo at one of those tags:

.. code-block:: bash

    $ git checkout -b PROD-hindcast_201905-v3 PROD-hindcast_201905-v3

and build XIOS-2 with:

.. code-block:: bash

    $ cd $PROJECT/SalishSeaCast/hindcast-sys/XIOS-2/
    $ ./make_xios --arch GCC_OPTIMUM --netcdf_lib netcdf4_seq --job 8

:kbd:`--netcdf_lib netcdf4_seq` is necessary because the :kbd:`OpenMPI/2.1.6/GCC/SYSTEM`  NetCDF libraries are not built for parallel output.

To clear away all artifacts of a previous build of XIOS-2 use:

.. code-block:: bash

    $ cd $PROJECT/SalishSeaCast/hindcast-sys/XIOS-2
    $ ./tools/FCM/bin/fcm build --clean


Build NEMO-3.6 and REBUILD_NEMO
===============================

Create a branch to checkout the repo at an appropriate tag:

* For hindcast runs,
  something like:

  .. code-block:: bash

      $ cd $PROJECT/SalishSeaCast/hindcast-sys/NEMO-3.6-code/
      $ git checkout -b PROD-hindcast_201905-v3 PROD-hindcast_201905-v3

* For research runs,
  something like:

  .. code-block:: bash

      $ cd $PROJECT/SalishSeaCast/hindcast-sys/NEMO-3.6-code/
      $ git checkout -b fluxes fluxes

Build NEMO-3.6 with:

.. code-block:: bash

    $ cd $PROJECT/SalishSeaCast/hindcast-sys/NEMO-3.6-code/NEMOGCM/CONFIG
    $ XIOS_HOME=$PROJECT/SalishSeaCast/hindcast-sys/XIOS-2/ ./makenemo -m GCC_OPTIMUM -n SalishSeaCast -j8

:program:`REBUILD_NEMO` requires a different collection of modules to be loaded for build and execution.
Build it with:

.. code-block:: bash

    $ module load GCC/8.3
    $ module load OpenMPI/2.1.6/GCC/8.3
    $ module load ZLIB/1.2/11
    $ module load use.paustin
    $ module load HDF5/1.08/20
    $ module load NETCDF/4.6/1
    $ cd $PROJECT/SalishSeaCast/hindcast-sys/NEMO-3.6-code/NEMO-3.6-code/NEMOGCM/TOOLS/
    $ ./maketools -m GCC_OPTIMUM_REBUILD_NEMO -n REBUILD_NEMO


Install Python Packages
=======================

Load the :kbd:`Miniconda/3` module and create a Conda environment:

.. code-block:: bash

    $ module load Miniconda/3
    $ conda create -n salishseacast -c conda-forge python=3 pip arrow \
      attrs cliff f90nml gitpython pyyaml
    $ source activate salishseacast
    (salishseacast)$ python3 -m pip install python-hglib

Install the SalishSeaCast NEMO-Cmd and SalishSeaCmd packages from their repo clones:

.. code-block:: bash

    (salishseacast)$ cd $PROJECT/SalishSeaCast/hindcast-sys/
    (salishseacast)$ python3 -m pip install --editable NEMO-Cmd/
    (salishseacast)$ python3 -m pip install --editable SalishSeaCmd/


Populate Run Preparation Directory
==================================

Copy the :file:`namelist.time` namelist section template file from the :file:`SS-run-sets` repo clone into the :file:`$PROJECT/SalishSeaCast/hindcast-sys/runs/` directory:

.. code-block:: bash

    $ cd $PROJECT/SalishSeaCast/hindcast-sys/runs/
    $ cp ../SS-run-sets/v201905/hindcast/namelist.time_template namelist.time

Symlink the run description YAML template file from the :file:`SS-run-sets` repo clone into the :file:`$PROJECT/SalishSeaCast/hindcast-sys/runs/` directory:

.. code-block:: bash

    $ cd $PROJECT/SalishSeaCast/hindcast-sys/runs/
    $ ln -s ../SS-run-sets/v201905/hindcast/optimum_hindcast_template.yaml hindcast_template.yaml

Create and populate forcing directory trees with:

.. code-block:: bash

    $ mkdir -p $FORCING/SalishSeaCast/forcing/atmospheric/GEM2.5/gemlam
    $ mkdir -p $FORCING/SalishSeaCast/forcing/atmospheric/GEM2.5/operational
    $ mkdir -p $FORCING/SalishSeaCast/forcing/LiveOcean
    $ mkdir -p $FORCING/SalishSeaCast/forcing/rivers/river_turb
    $ mkdir -p $FORCING/SalishSeaCast/forcing/sshNeahBay/fcst
    $ mkdir -p $FORCING/SalishSeaCast/forcing/sshNeahBay/obs

The :file:`upload_forcing` worker will upload daily forcing files to these directories.
