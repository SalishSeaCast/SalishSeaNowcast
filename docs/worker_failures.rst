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

.. _MitigatingWorkerFailures:

**************************
Mitigating Worker Failures
**************************

:py:mod:`get_NeahBay_ssh` Worker Failure
========================================

The sea surface height anomaly at the western Juan de Fuca boundary is taken from a `NOAA forecast`_ of storm surge at Neah Bay.
If this page is not accessible then the :mod:`get_NeahBay_ssh` worker may fail.
In this case, we can recover observed sea surface heights from the `NOAA tides and water levels`_ which may be used in the future.

To recover the observed sea surface anomaly, run through this `SSH_NeahBay`_ notebook with the appropriate date.
The notebook is located in :file:`SalishSeaNowcast/nowcast/notebooks/SSH_NeahBay.ipynb`.

This notebook calculates the sea surface height anomaly by removing tidal predictions from the NOAA Neah Bay observations.
It then saves the result in a netCDF file for use in NEMO simulations.

.. _NOAA forecast: http://www.nws.noaa.gov/mdl/etsurge/index.php?page=stn&region=wc&datum=mllw&list=&map=0-48&type=both&stn=waneah

.. _NOAA tides and water levels: https://tidesandcurrents.noaa.gov/waterlevels.html?id=9443090

.. _SSH_NeahBay: https://nbviewer.jupyter.org/url/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/SSH_NeahBay.ipynb


:py:mod:`download_weather` Worker Failure
=========================================

The Environment Canada (EC) 2.5 km resolution GEM forecast model products from the High Resolution Deterministic Prediction System (HRDPS) are critical inputs for the nowcast system.
They are also the only input source that is transient -
each of the 4 daily forecast data sets are only available for slightly over a day,
and EC does not maintain an archive of the HRDPS products.

The HRDPS products files that we use are downloaded every 6 hours via the :py:mod:`SalishSeaNowcast.nowcast.workers.download_weather` worker.
The downloads are controlled by 4 :program:`cron` jobs that run on :kbd:`skookum`:

  * The :kbd:`06` UTC forecast download starts at 05:00 Pacific time
  * The :kbd:`12` UTC forecast download starts at 11:00 Pacific time
  * The :kbd:`18` UTC forecast download starts at 17:00 Pacific time
  * The :kbd:`00` UTC forecast download starts at 23:00 Pacific time

The :py:mod:`download_weather` worker uses an exponential back-off and retry strategy to try very hard to get the required files in the face of network congestion and errors.
If things are going really badly it can take nearly 5 hours to complete or fail to complete a forecast download.
If a failure does occur the `info log file`_ will contain a :kbd:`CRITICAL` message like::

  2015-07-08 10:00:03 INFO [download_weather] downloading 12 forecast GRIB2 files for 20150708
  2015-07-08 14:57:29 CRITICAL [download_weather] unhandled exception:
  2015-07-08 14:57:29 ERROR [download_weather] Traceback (most recent call last):
  ...

followed by the traceback from the error that caused the failure.
The `debug log file`_ will show more details about the specific file downloads and will also include the :kbd:`CRITICAL` log message.

.. _info log file: https://salishsea.eos.ubc.ca/nemo/nowcast/logs/nowcast.log
.. _debug log file: https://salishsea.eos.ubc.ca/nemo/nowcast/logs/nowcast.debug.log

In the rare event that the nowcast automation system fails to download the HRDPS products every 6 hours via the :py:mod:`SalishSeaNowcast.nowcast.workers.download_weather` worker,
it is critical that someone re-run that worker.
That can be accomplished as follows:

#. :command:`ssh` on to :kbd:`skookum`,
   activate the production nowcast :program:`conda` environment,
   and navigate to the nowcast configuration and logging directory:

   .. code-block:: bash

       $ ssh skookum
       skookum$ source activate /SalishSeaCast/nowcast-env
       (/SalishSeaCast/nowcast-env)skookum$ cd /home/dlatorne/public_html/MEOPAR/nowcast/

   .. note::
      If :command:`source activate /SalishSeaCast/nowcast-env` fails because it can't find :command:`activate`,
      you may be able to use:

      .. code-block:: bash

          skookum$ source /SalishSeaCast/nowcast-env/bin/activate /SalishSeaCast/nowcast-env

      as a work-around.

#. Run the :py:mod:`SalishSeaNowcast.nowcast.workers.download_weather` worker for the appropriate forecast with debug logging,
   for example:

   .. code-block:: bash

       (/SalishSeaCast/nowcast-env)skookum$ python -m nowcast.workers.download_weather $NOWCAST_YAML 12 --debug

   The command above downloads the 12 forecast.
   The :kbd:`--debug` flag causes the logging output of the worker to be displayed on the screen (so that you can see what is going on) instead of being written to a file.
   It also disconnects the worker from the nowcast messaging system so that there is no interaction with the manager and the ongoing automation.
   The (abridged) output should look like::

     2015-07-08 17:59:34 DEBUG [download_weather] running in process 5506
     2015-07-08 17:59:34 DEBUG [download_weather] read config from nowcast.yaml
     2015-07-08 17:59:34 DEBUG [download_weather] connected to localhost port 5555
     2015-07-08 17:59:34 INFO [download_weather] downloading 12 forecast GRIB2 files for 20150708
     2015-07-08 17:59:34 INFO [download_weather] downloading 12 forecast GRIB2 files for 20150708
     2015-07-08 17:59:37 DEBUG [download_weather] downloaded 248557 bytes from http://dd.weather.gc.ca/model_hrdps/west/grib2/12/001/CMC_hrdps_west_UGRD_TGL_10_ps2.5km_2015070812_P001-00.grib2
     2015-07-08 17:59:40 DEBUG [download_weather] downloaded 253914 bytes from http://dd.weather.gc.ca/model_hrdps/west/grib2/12/001/CMC_hrdps_west_VGRD_TGL_10_ps2.5km_2015070812_P001-00.grib2
     2015-07-08 17:59:42 DEBUG [download_weather] downloaded 47222 bytes from http://dd.weather.gc.ca/model_hrdps/west/grib2/12/001/CMC_hrdps_west_DSWRF_SFC_0_ps2.5km_2015070812_P001-00.grib2

     ...

     2015-07-08 18:16:49 DEBUG [download_weather] downloaded 71893 bytes from http://dd.weather.gc.ca/model_hrdps/west/grib2/12/048/CMC_hrdps_west_APCP_SFC_0_ps2.5km_2015070812_P048-00.grib2
     2015-07-08 18:16:52 DEBUG [download_weather] downloaded 135163 bytes from http://dd.weather.gc.ca/model_hrdps/west/grib2/12/048/CMC_hrdps_west_PRMSL_MSL_0_ps2.5km_2015070812_P048-00.grib2
     2015-07-08 18:16:52 INFO [download_weather] weather forecast 12 downloads complete
     2015-07-08 18:16:52 INFO [download_weather] weather forecast 12 downloads complete
     2015-07-08 18:16:52 DEBUG [download_weather] sent message: (success 12) 12 weather forecast ready
     ^C
     2015-07-08 18:22:52 INFO [download_weather] interrupt signal (SIGINT or Ctrl-C) received; shutting down
     2015-07-08 18:22:52 INFO [download_weather] interrupt signal (SIGINT or Ctrl-C) received; shutting down
     ^C
     2015-07-08 18:22:57 INFO [download_weather] interrupt signal (SIGINT or Ctrl-C) received; shutting down
     2015-07-08 18:22:57 INFO [download_weather] interrupt signal (SIGINT or Ctrl-C) received; shutting down
     2015-07-08 18:22:57 DEBUG [download_weather] task completed; shutting down

You can use the :kbd:`-h` or :kbd:`--help` flags to get a usage message that explains the worker's required arguments,
and its option flags:

.. code-block:: bash

    (nowcast)$ python -m nowcast.workers.download_weather --help

.. code-block:: none

    usage: python -m nowcast.workers.download_weather
           [-h] [--debug] [--yesterday] config_file {18,00,12,06}

    Salish Sea NEMO nowcast weather model dataset download worker. Download the
    GRIB2 files from today's 00, 06, 12, or 18 EC GEM 2.5km HRDPS operational
    model forecast.

    positional arguments:
      config_file    Path/name of YAML configuration file for Salish Sea NEMO
                     nowcast.
      {18,00,12,06}  Name of forecast to download files from.

    optional arguments:
      -h, --help     show this help message and exit
      --debug        Send logging output to the console instead of the log file;
                     intended only for use when the worker is run in foreground
                     from the command-line.
      --yesterday    Download forecast files for previous day's date.

The :kbd:`--yesterday` flag allows you to download the previous day's forecast files.
Use that flag only during the several hour period for which two day's forecast files exist in the http://dd.weather.gc.ca/model_hrdps/west/grib2/ file space.
To determine if the :kbd:`--yesterday` flag can be used check the contents of a forecast's hourly directories;
e.g. http://dd.weather.gc.ca/model_hrdps/west/grib2/06/001/,
to see if files for 2 days exist.

Even if the worker cannot be re-run in the nowcast system deployment environment on :kbd:`skookum` due to permission issues the forecast products can be downloaded using a :ref:`SalishSeaNowcastDevelopmentEnvironment`.
That can be accomplished as follows:

#. Activate your nowcast :program:`conda` environment,
   and navigate to your nowcast development and testing environment:

   .. code-block:: bash

       $ source activate salishsea-nowcast
       (nowcast)$ cd MEOPAR/nowcast/

#. Edit the :file:`SalishSeaNowcast/config/nowcast.yaml` file to set a destination in your filespace for the GRIB2 files that the worker downloads:

   .. code-block:: yaml

       weather:
         download:
           # Destination directory for downloaded GEM 2.5km operational model GRIB2 files
           # GRIB dir: /results/forcing/atmospheric/GEM2.5/GRIB/
           GRIB dir: /ocean/<your_userid>/MEOPAR/GRIB/

   .. note::

        The directory :file:`/ocean/<your_userid>/MEOPAR/GRIB/` must exist.
        Create it if necessary with:

        .. code-block:: bash

            $ mkdir -p /ocean/<your_userid>/MEOPAR/GRIB/

#. Set the value of the :envvar:`NOWCAST_YAML` environment variable to the absolute path the :file:`SalishSeaNowcast/config/nowcast.yaml` file that you edited.

#. Continue from step 2 above.
