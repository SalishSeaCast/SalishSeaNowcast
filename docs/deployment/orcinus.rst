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

.. _OrcinusDeployment:

*******************************************************
:kbd:`orcinus` Deployment for :kbd:`nowcast-agrif` Runs
*******************************************************

Create Directory Trees
======================

Create directory trees for the run preparation directory,
Mercurial repositories,
temporary run directories,
and results directories,
and set their groups and permissions:

.. code-block:: bash

    $ mkdir -p /home/dlatorne/nowcast-agrif-sys/runs
    $ chgrp wg-moad /home/dlatorne/nowcast-agrif-sys/
    $ chmod g+ws /home/dlatorne/nowcast-agrif-sys/
    $ chmod g+w /home/dlatorne/nowcast-agrif-sys/runs
    $ mkdir -p /global/scratch/dlatorne/nowcast-agrif
    $ chgrp wg-moad /global/scratch/dlatorne/nowcast-agrif
    $ chmod g+ws /global/scratch/dlatorne/nowcast-agrif


Clone Git Repositories
======================

Clone the following repos into :file:`/home/dlatorne/nowcast-agrif-sys/`:

.. code-block:: bash

    $ cd /home/dlatorne/nowcast-agrif-sys/
    $ git clone git@github.com:SalishSeaCast/grid.git
    $ git clone git@github.com:SalishSeaCast/NEMO-Cmd.git
    $ git clone git@github.com:SalishSeaCast/rivers-climatology.git
    $ git clone git@github.com:SalishSeaCast/SalishSeaCmd.git
    $ git clone git@github.com:SalishSeaCast/tides.git
    $ git clone git@github.com:SalishSeaCast/tracers.git
    $ git clone git@github.com:SalishSeaCast/XIOS-ARCH.git


Clone Mercurial Repositories
============================

Clone the following repos into :file:`/home/dlatorne/nowcast-agrif-sys/`:

.. code-block:: bash

    $ cd /home/dlatorne/nowcast-agrif-sys/
    $ hg clone ssh://hg@bitbucket.org/salishsea/nemo-3.6-code NEMO-3.6-code
    $ hg clone ssh://hg@bitbucket.org/salishsea/ss-run-sets SS-run-sets
    $ hg clone ssh://hg@bitbucket.org/salishsea/xios-2 XIOS-2


Build XIOS-2
============

Symlink the XIOS-2 build configuration files for :kbd:`orcinus` from the :file:`XIOS-ARCH` repo clone into the :file:`XIOS-2/arch/` directory:

.. code-block:: bash

    $ cd /home/dlatorne/nowcast-agrif-sys/XIOS-2/arch
    $ ln -s ../../XIOS-ARCH/UBC-EOAS/arch-X64_ORCINUS.fcm
    $ ln -s ../../XIOS-ARCH/UBC-EOAS/arch-X64_ORCINUS.path

and build XIOS-2 with:

.. code-block:: bash

    $ cd /home/dlatorne/nowcast-agrif-sys/XIOS-2
    $ ./make_xios --arch X64_ORCINUS --netcdf_lib netcdf4_seq --job 8


Build NEMO-3.6
==============

Build NEMO-3.6 and :program:`rebuild_nemo.exe`:

.. code-block:: bash

    $ cd /home/dlatorne/nowcast-agrif-sys/NEMO-3.6-code/NEMOGCM/CONFIG
    $ ./makenemo -m X64_ORCINUS -n SMELTAGRIF -j8
    $ cd /home/dlatorne/nowcast-agrif-sys/NEMO-3.6-code/NEMOGCM/TOOLS/
    $ ./maketools -m X64_ORCINUS -n REBUILD_NEMO


Install Python Packages
=======================

The Python packages that the system depends on are installed as user packages in :file:`/home/dlatorne/.local/bin/` with:

.. code-block:: bash

    $ cd /home/dlatorne/nowcast-agrif-sys/
    $ python3 -m pip install --user --editable NEMO-Cmd/
    $ python3 -m pip install --user --editable SalishSeaCmd/


Populate Run Preparation Directory Tree
=======================================

Copy the :file:`namelist.time` namelist section files from the :file:`SS-run-sets` repo clone into the :file:`/home/dlatorne/nowcast-agrif-sys/runs/` directory:

.. code-block:: bash

    $ cd /home/dlatorne/nowcast-agrif-sys/runs/
    $ cp ../SS-run-sets/v201702/smelt-agrif/namelist.time.template namelist.time
    $ cp ../SS-run-sets/v201702/smelt-agrif/namelist.time.BS.template namelist.time
    $ cp ../SS-run-sets/v201702/smelt-agrif/namelist.time.HS.template namelist.time

Symlink the run description YAML template files from the :file:`SS-run-sets` repo clone into the :file:`/home/dlatorne/nowcast-agrif-sys/runs/` directory:

.. code-block:: bash

    $ cd /home/dlatorne/nowcast-agrif-sys/runs/
    $ ln -s ../SS-run-sets/v201702/smelt-agrif/orcinus_nowcast_template.yaml nowcast-agrif_template.yaml

Create an populate forcing sub-directories with:

.. code-block:: bash

    $ cd /home/dlatorne/nowcast-agrif-sys/runs/
    $ mkdir -p LiveOcean NEMO-atmos rivers ssh
    $ chmod g+w LiveOcean NEMO-atmos rivers ssh
    $ cd NEMO-atmos/
    $ cd rivers/
    $ ln -s /home/dlatorne/nowcast-agrif-sys/rivers-climatology/bio

The :file:`make_forcing_links` worker will create symlinks to the appropriate forcing files in the :file:`LiveOcean`,
:file:`NEMO-atmos`,
:file:`rivers`,
and :file:`ssh` directories.


Sub-grid Initialization Preparation with Nesting Tools
======================================================

Build Nesting Tools
-------------------

Clone Michael Dunphies' debugged version of the nesting tools for AGRIF from :file:`NEMO-3.6-code/NEMOGCM/TOOLS/NESTING/` on to :kbd:`salish`:

.. code-block:: bash

    $ ssh salish
    $ cd /data/dlatorne/MEOPAR/
    $ git clone git@github.com:SalishSeaCast/NestingTools.git

Build the nesting tools suite of Fortran programs with:

.. code-block:: bash

    $ cd /data/dlatorne/MEOPAR/NestingTools/NEMOGCM/TOOLS
    $ ./maketools -n NESTING -m GCC_SALISH


Generate Sub-grid Files
-----------------------

Set up a working directory tree in which to generate the sub-grid files:

.. code-block:: bash

    $ cd /results/nowcast-sys/
    $ mkdir -p agrif-nesting/BaynesSound agrif-nesting/HaroStrait
    $ cd /results/nowcast-sys/BaynesSound/
    $ ln -s /results/nowcast-sys/SS-run-sets/v201702/smelt-agrif/nesting/namelist.nesting.BaynesSound
    $ cd /results/nowcast-sys/HaroStrait
    $ ln -s /results/nowcast-sys/SS-run-sets/v201702/smelt-agrif/nesting/namelist.nesting.HaroStrait

Some of the nesting tools processes take ~1hr to run,
so it is probably best to run them in a :program:`tmux` session.


Coordinates
^^^^^^^^^^^

For the Baynes Sound sub-grid,
use :program:`agrif_create_coordinates.exe` to create the sub-grid coordinates file from the full domain coordinates
(path provided in the :file:`namelist.nesting.BaynesSound` file),
and add it to the :kbd:`grid` repo:

.. code-block:: bash

    $ cd /results/nowcast-sys/agrif-nesting/BaynesSound/
    $ /data/dlatorne/MEOPAR/NestingTools/NEMOGCM/TOOLS/NESTING/agrif_create_coordinates.exe \
        namelist.nesting.BaynesSound
    $ cp 1_coordinates_seagrid_SalishSea201702.nc \
        /results/nowcast-sys/grid/subgrids/BaynesSound/coordinates_seagrid_SalishSea201702_BS.nc
    $ cd /results/nowcast-sys/grid/
    $ hg add /results/nowcast-sys/grid/subgrids/BaynesSound/coordinates_seagrid_SalishSea201702_BS.nc
    $ hg commit subgrids/BaynesSound/coordinates_seagrid_SalishSea201702_BS.nc \
        -m"Add coordinates for 201702 bathymetry in Baynes Sound AGRIF sub-grid."

Similarly for the Haro Strait sub-grid:

.. code-block:: bash

    $ cd /results/nowcast-sys/agrif-nesting/HaroStrait/
    $ /data/dlatorne/MEOPAR/NestingTools/NEMOGCM/TOOLS/NESTING/agrif_create_coordinates.exe \
        namelist.nesting.HaroStrait
    $ cp 1_coordinates_seagrid_SalishSea201702.nc \
        /results/nowcast-sys/grid/subgrids/HaroStrait/coordinates_seagrid_SalishSea201702_HS.nc
    $ cd /results/nowcast-sys/grid/
    $ hg add /results/nowcast-sys/grid/subgrids/HaroStrait/coordinates_seagrid_SalishSea201702_HS.nc
    $ hg commit subgrids/HaroStrait/coordinates_seagrid_SalishSea201702_HS.nc \
        -m"Add coordinates for 201702 bathymetry in Haro Strait AGRIF sub-grid."


Bathymetry
^^^^^^^^^^

.. note::
    Need to understand the details of how sub-grid bathymetries are generated.
    They appear to be based on :file:`/home/mdunphy/MEOPAR/WORK/Bathy-201702/BC3/BC3_For_Nesting_Tools.nc` and a :kbd:`bathymetry` namelist like:

    .. code-block:: bash

        &bathymetry
            new_topo = true
            elevation_database = '/home/mdunphy/MEOPAR/WORK/Bathy-201702/BC3/BC3_For_Nesting_Tools.nc'
            elevation_name = 'Bathymetry'
            smoothing = true
            smoothing_factor = 0.6
            nb_connection_pts = 3
            removeclosedseas = false
            type_bathy_interp = 2
            rn_hmin = 3
        /

    There is also subsequent processing by :program:`analysis-michael/agrif/fix_bathy.py` to "enforce minimum depth and fix the longitudes".


Rivers Biology Tracers Climatology Mean File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Because the Fraser River is the only river in the model for which we have daily varying values in its biological tracer values,
we can construct an acceptable rivers biological tracers forcing file for the Baynes Sound sub-grid by averaging the daily Climatology files.

.. warning::
    This will have to be revisited if/when we change the Puntledge River to use real-time discharges values from a gauge.

Calculate the :file:`rivers-climatology/bio/subgrids/BaynesSound/bio/rivers_bio_tracers_mean.nc`,
and add it to the :kbd:`rivers-climatology` repo:

.. code-block:: bash

    $ cd rivers-climatology/bio
    $ mkdir -p ../subgrids/BaynesSound/bio
    $ /bin/ls | grep rivers_bio_tracers_'m..d..'.nc | \
        ncra -4 -o ../subgrids/BaynesSound/bio/rivers_bio_tracers_mean.nc
    $ hg add rivers-climatology/subgrids/BaynesSound/bio/rivers_bio_tracers_mean.nc
    $ hg commit rivers-climatology/subgrids/BaynesSound/bio/rivers_bio_tracers_mean.nc \
      -m"Add rivers biology tracers climatology mean file for Baynes Sound"


Physics Restart Files
^^^^^^^^^^^^^^^^^^^^^

The commands in this section are for generation of sub-grid physics restart files from the :file:`nowcast-green/12may18/SalishSea_02935440_restart.nc` file
(path provided in the :file:`namelist.nesting.BaynesSound` and :file:`namelist.nesting.HaroStrait` files).

For the Baynes Sound sub-grid,
use :program:`agrif_create_restart.exe` to create the sub-grid physics restart file from the full domain physics restart file,
and upload both files to the appropriate run results directory on :kbd:`orcinus`:

.. code-block:: bash

    $ cd /results/nowcast-sys/agrif-nesting/BaynesSound/
    $ /data/dlatorne/MEOPAR/NestingTools/NEMOGCM/TOOLS/NESTING/agrif_create_restart.exe \
        namelist.nesting.BaynesSound
    $ scp /results/SalishSea/nowcast-green/12may18/SalishSea_02935440_restart.nc \
        orcinus:/global/scratch/dlatorne/nowcast-agrif/12may18/
    $ scp 1_SalishSea_02935440_restart.nc \
        orcinus:/global/scratch/dlatorne/nowcast-agrif/12may18/2_SalishSea_05870880_restart.nc

Note that the time step number in the Baynes Sound sub-grid restart file name is 2x that of the full domain file because the Baynes Sound sub-grid time step is 20s in contrast to 40s for the full domain.

Similarly for the Haro Strait sub-grid:

.. code-block:: bash

    $ cd /results/nowcast-sys/agrif-nesting/HaroStrait/
    $ /data/dlatorne/MEOPAR/NestingTools/NEMOGCM/TOOLS/NESTING/agrif_create_restart.exe \
        namelist.nesting.HaroStrait
    $ scp 1_SalishSea_02935440_restart.nc \
        orcinus:/global/scratch/dlatorne/nowcast-agrif/12may18/1_SalishSea_11741760_restart.nc

Note that the time step number in the Haro Strait sub-grid restart file name is 4x that of the full domain file because the Haro Strait sub-grid time step is 10s in contrast to 40s for the full domain.


Tracer Restart Files
^^^^^^^^^^^^^^^^^^^^

The commands in this section are for generation of sub-grid tracer restart files from the :file:`nowcast-green/12may18/SalishSea_02935440_restart_trc.nc` file
(path provided in the :file:`namelist.nesting.BaynesSound` and :file:`namelist.nesting.HaroStrait` files).

For the Baynes Sound sub-grid,
use :program:`agrif_create_restart_trc.exe` to create the sub-grid tracer restart file from the full domain tracer restart file,
and upload both files to the appropriate run results directory on :kbd:`orcinus`:

.. code-block:: bash

    $ cd /results/nowcast-sys/agrif-nesting/BaynesSound/
    $ /data/dlatorne/MEOPAR/NestingTools/NEMOGCM/TOOLS/NESTING/agrif_create_restart_trc.exe \
        namelist.nesting.BaynesSound
    $ scp /results/SalishSea/nowcast-green/12may18/SalishSea_02935440_restart_trc.nc \
        orcinus:/global/scratch/dlatorne/nowcast-agrif/12may18/
    $ scp 1_SalishSea_02935440_restart_trc.nc \
        orcinus:/global/scratch/dlatorne/nowcast-agrif/12may18/2_SalishSea_05870880_restart_trc.nc

Note that the time step number in the Baynes Sound sub-grid restart file name is 2x that of the full domain file because the Baynes Sound sub-grid time step is 20s in contrast to 40s for the full domain.

For Haro Strait,
start by using :program:`agrif_create_restart_trc.exe` to create the sub-grid tracer restart file from the full domain tracer restart file:

.. code-block:: bash

    $ cd /results/nowcast-sys/agrif-nesting/HaroStrait/
    $ /data/dlatorne/MEOPAR/NestingTools/NEMOGCM/TOOLS/NESTING/agrif_create_restart_trc.exe \
        namelist.nesting.HaroStrait

For some reason :program:`agrif_create_restart_trc.exe` fails to store the variable :kbd:`TRBTRA`
(the Fraser River tracer :kbd:`B` field, and the final variable)
in the file it produces.
To deal with that we duplicate the :kbd:`TRNTRA` field values as :kbd:`TRBTRA` and append that variable to the file:

.. code-block:: bash

    $ ncks -4 -O -v TRNTRA 1_SalishSea_02935440_restart_trc.nc TRNTRA.nc
    $ ncks -4 -O 1_SalishSea_02935440_restart_trc.nc 1_SalishSea_02935440_restart_trc.nc
    $ ncrename -O -v TRNTRA,TRBTRA TRNTRA.nc TRBTRA.nc
    $ ncks -4 -A TRBTRA.nc 1_SalishSea_02935440_restart_trc.nc

and upload the file to the appropriate run results directory on :kbd:`orcinus`:

.. code-block:: bash

    $ scp 1_SalishSea_02935440_restart_trc.nc \
        orcinus:/global/scratch/dlatorne/nowcast-agrif/12may18/1_SalishSea_11741760_restart_trc.nc

Note that the time step number in the Haro Strait sub-grid restart file name is 4x that of the full domain file because the Haro Strait sub-grid time step is 10s in contrast to 40s for the full domain.
