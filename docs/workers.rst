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


.. _SalishSeaNowcastSystemWorkers:

*********************************
Salish Sea Nowcast System Workers
*********************************

Process Flow
============

.. figure:: ProcessFlow.png
    :align: center

    Work flow of preparation for and execution of the daily runs.

The green,
pink,
and blue boxes in the figure above are the workers described below.

The other workers are launched and coordinated by the :ref:`nemonowcast:SystemManager`,
another long-running process that keeps track of the state of the nowcast system.
The workers and manager communicate by using the :ref:`nemonowcast:MessagingSystem` to pass messages back and forth.

The messages are mediated by the :ref:`nemonowcast:MessageBroker`,
a third long-running process that queues messages in both directions between the manager and the workers.
That queuing improves the robustness of the system.

Please see :ref:`nemonowcast:FrameworkArchitecture` for a more detailed description of the system architecture.

The process flow in the diagram above is somewhat idealized.
For example:

* The :py:mod:`~nowcast.workers.collect_weather` worker is launched four times daily,
  to get the hour 00, 06, 12, and 18 UTC forecast products.
* The :py:mod:`~nowcast.workers.make_runoff_file` worker is launched both after the 06 forecast
  download finishes to calculate the river runoff forcing for the preliminary forecast runs
  from the previous day's ECCC gauged rivers average discharge values.
  It is launched again to update the river runoff forcing for the nowcast and final forecast
  runs with the previous day's USGS gauged rivers average discharge values that are unavailable at
  preliminary forecast time.
* The :py:mod:`~nowcast.workers.grib_to_netcdf` worker is only launched after the
  06 and 12 forecast downloads finish to prepare the atmospheric forcing files that will
  be used by the preliminary forecast run,
  and the nowcast and updated forecast runs.
  However,
  :py:mod:`~nowcast.workers.grib_to_netcdf` uses results from several preceding forecast
  products downloads to do its job.
* Etc.

To fully understand the flow and interactions of workers,
please read the code in the :py:mod:`nowcast.next_workers` module.


Workers
=======

.. _CollectWeatherWorker:

``collect_weather``
--------------------

.. automodule:: nowcast.workers.collect_weather
    :members: main


.. _DownloadWeatherWorker:

``download_weather``
--------------------

.. automodule:: nowcast.workers.download_weather
    :members: main


.. _CropGribsWorker:

``crop_gribs``
------------------

.. automodule:: nowcast.workers.crop_gribs
    :members: main


.. _GribToNetcdfWorker:

``grib_to_netcdf``
------------------

.. automodule:: nowcast.workers.grib_to_netcdf
    :members: main


``collect_river_data``
----------------------

.. automodule:: nowcast.workers.collect_river_data
    :members: main


``make_201702_runoff_file``
---------------------------

.. automodule:: nowcast.workers.make_201702_runoff_file
    :members: main


``make_runoff_file``
--------------------

.. automodule:: nowcast.workers.make_runoff_file
    :members: main


.. _CollectNeahBaySshWorker:

``collect_NeahBay_ssh``
-----------------------

.. automodule:: nowcast.workers.collect_NeahBay_ssh
    :members: main


.. _MakeSshFilesWorker:

``make_ssh_files``
------------------

.. automodule:: nowcast.workers.make_ssh_files
    :members: main


.. _DownloadLiveOceanWorker:

``download_live_ocean``
-----------------------

.. automodule:: nowcast.workers.download_live_ocean
    :members: main


.. _MakeLiveOceanFilesWorker:

``make_live_ocean_files``
-------------------------

.. automodule:: nowcast.workers.make_live_ocean_files
    :members: main


.. _UploadForcingWorker:

``upload_forcing``
------------------

.. automodule:: nowcast.workers.upload_forcing
    :members: main


``make_forcing_links``
----------------------

.. automodule:: nowcast.workers.make_forcing_links
    :members: main


``run_NEMO``
------------

.. automodule:: nowcast.workers.run_NEMO
    :members: main


``run_NEMO_agrif``
------------------

.. automodule:: nowcast.workers.run_NEMO_agrif
    :members: main


``run_NEMO_hindcast``
---------------------

.. automodule:: nowcast.workers.run_NEMO_hindcast
    :members: main


.. _WatchNEMO-Worker:

``watch_NEMO``
--------------

.. automodule:: nowcast.workers.watch_NEMO
    :members: main


``watch_NEMO_agrif``
--------------------

.. automodule:: nowcast.workers.watch_NEMO_agrif
    :members: main


``watch_NEMO_hindcast``
-----------------------

.. automodule:: nowcast.workers.watch_NEMO_hindcast
    :members: main


``make_turbidity_file``
-----------------------

.. automodule:: nowcast.workers.make_turbidity_file
    :members: main


.. _MakeWW3WindFile-Worker:

``make_ww3_wind_file``
----------------------

.. automodule:: nowcast.workers.make_ww3_wind_file
    :members: main


.. _MakeWW3CurrentFile-Worker:

``make_ww3_current_file``
-------------------------

.. automodule:: nowcast.workers.make_ww3_current_file
    :members: main


``run_ww3``
------------

.. automodule:: nowcast.workers.run_ww3
    :members: main


``watch_ww3``
--------------

.. automodule:: nowcast.workers.watch_ww3
    :members: main


``download_results``
--------------------

.. automodule:: nowcast.workers.download_results
    :members: main


``make_averaged_dataset``
-------------------------

.. automodule:: nowcast.workers.make_averaged_dataset
    :members: main


``archive_tarball``
-------------------

.. automodule:: nowcast.workers.archive_tarball
    :members: main


``split_results``
-----------------

.. automodule:: nowcast.workers.split_results
    :members: main


``download_wwatch3_results``
----------------------------

.. automodule:: nowcast.workers.download_wwatch3_results
    :members: main


``download_fvcom_results``
--------------------------

.. automodule:: nowcast.workers.download_fvcom_results
    :members: main


``get_onc_ctd``
---------------

.. automodule:: nowcast.workers.get_onc_ctd
    :members: main


``update_forecast_datasets``
----------------------------

.. automodule:: nowcast.workers.update_forecast_datasets
    :members: main


``ping_erddap``
---------------

.. automodule:: nowcast.workers.ping_erddap
    :members: main


.. _MakePlotsWorker:

``make_plots``
--------------

.. automodule:: nowcast.workers.make_plots
    :members: main


``make_surface_current_tiles``
------------------------------

.. automodule:: nowcast.workers.make_surface_current_tiles
    :members: main


``make_feeds``
--------------

.. automodule:: nowcast.workers.make_feeds
    :members: main


``clear_checklist``
-------------------

.. automodule:: nemo_nowcast.workers.clear_checklist
    :members: main


``rotate_logs``
---------------

.. automodule:: nemo_nowcast.workers.rotate_logs
    :members: main


Worker Utility Functions
------------------------

:py:mod:`nowcast.lib` Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nowcast.lib
    :members:


Special Workers
---------------

``launch_remote_worker``
^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nowcast.workers.launch_remote_worker
    :members: main


``rotate_hindcast_logs``
^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nowcast.workers.rotate_hindcast_logs
    :members: main


:py:mod:`next_workers` Module
=============================

.. automodule:: nowcast.next_workers
    :members:


.. _nowcast.figures:

Results Figures Modules
=======================

The modules in the :py:obj:`nowcast.figures` namespace are used by the :ref:`MakePlotsWorker` worker to produce the figures that are published to the web from each run.
The figures are also stored in the :file:`figures/` sub-directory of each run's results directory.


.. _nowcast.figures.shared:

:py:mod:`nowcast.figures.shared` Module
---------------------------------------

.. automodule:: nowcast.figures.shared
    :members:


.. _nowcast.figures.website_theme:

:py:mod:`nowcast.figures.website_theme` Module
----------------------------------------------

.. automodule:: nowcast.figures.website_theme
    :members:


.. _nowcast.figures.surface_current_domain:

:py:mod:`nowcast.figures.surface_current_domain` Module
-------------------------------------------------------

.. automodule:: nowcast.figures.surface_current_domain
    :members:


.. _nowcast.figures.fvcom:

:py:obj:`nowcast.figures.fvcom`  Figure Modules
-----------------------------------------------

.. _nowcast.figures.fvcom.publish.tide_stn_water_level:

:py:mod:`nowcast.figures.fvcom.publish.tide_stn_water_level` Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nowcast.figures.fvcom.publish.tide_stn_water_level
    :members:


.. _nowcast.figures.fvcom.publish.second_narrows_current:

:py:mod:`nowcast.figures.fvcom.publish.second_narrows_current` Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nowcast.figures.fvcom.publish.second_narrows_current
    :members:


.. _nowcast.figures.fvcom.research.surface_currents:

:py:mod:`nowcast.figures.fvcom.research.surface_currents` Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nowcast.figures.fvcom.research.surface_currents
    :members:


.. _nowcast.figures.fvcom.research.thalweg_transect:

:py:mod:`nowcast.figures.fvcom.research.thalweg_transect` Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nowcast.figures.fvcom.research.thalweg_transect
    :members:



.. _nowcast.figures.comparison:

:py:obj:`nowcast.figures.comparison`  Figure Modules
----------------------------------------------------

.. _nowcast.figures.comparison.sandheads_winds:

:py:mod:`nowcast.figures.comparison.sandheads_winds` Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nowcast.figures.comparison.sandheads_winds
    :members:


.. _nowcast.figures.comparison.salinity_ferry_track:

:py:mod:`nowcast.figures.comparison.salinity_ferry_track` Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nowcast.figures.comparison.salinity_ferry_track
    :members:



.. _nowcast.figures.publish:

:py:obj:`nowcast.figures.publish`  Figure Modules
-------------------------------------------------

.. _nowcast.figures.publish.compare_tide_prediction_max_ssh:

:py:mod:`nowcast.figures.publish.compare_tide_prediction_max_ssh`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nowcast.figures.publish.compare_tide_prediction_max_ssh
    :members:


.. _nowcast.figures.publish.pt_atkinson_tide:

:py:mod:`nowcast.figures.publish.pt_atkinson_tide` Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nowcast.figures.publish.pt_atkinson_tide
    :members:


.. _nowcast.figures.publish.storm_surge_alerts:

:py:mod:`nowcast.figures.publish.storm_surge_alerts` Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nowcast.figures.publish.storm_surge_alerts
    :members:


.. _nowcast.figures.publish.storm_surge_alerts_thumbnail:

:py:mod:`nowcast.figures.publish.storm_surge_alerts_thumbnail` Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nowcast.figures.publish.storm_surge_alerts_thumbnail
    :members:


.. _nowcast.figures.publish.surface_current_tiles:

:py:mod:`nowcast.figures.publish.surface_current_tiles` Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nowcast.figures.publish.surface_current_tiles
    :members:


.. _nowcast.figures.research:

:py:obj:`nowcast.figures.research`  Figure Modules
--------------------------------------------------

.. _nowcast.figures.research.tracer_thalweg_and_surface:

:py:mod:`nowcast.figures.research.tracer_thalweg_and_surface` Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nowcast.figures.research.tracer_thalweg_and_surface
    :members:

.. _nowcast.figures.research.time_series_plots:

:py:mod:`nowcast.figures.research.time_series_plots` Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nowcast.figures.research.time_series_plots
    :members:


.. _nowcast.figures.wwatch3:

:py:obj:`nowcast.figures.wwatch3`  Figure Modules
-------------------------------------------------

.. _nowcast.figures.wwatch3.tide_stn_water_level:

:py:mod:`nowcast.figures.wwatch3.wave_height_period` Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nowcast.figures.wwatch3.wave_height_period
    :members:
