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


.. _MitigatingWorkerFailures:

**************************
Mitigating Worker Failures
**************************

:py:mod:`collect_NeahBay_ssh` Worker Failure
============================================

The sea surface height anomaly at the western Juan de Fuca boundary is taken from a
`NOAA forecast`_ of storm surge at Neah Bay.
If this page is not accessible then the
:py:mod:`nowcast.workers.collect_NeahBay_ssh` worker may fail.
As the observations for several days are saved in the files on this pages,
one can try at a later time and if necessary use yesterday's files to continue the forecast.
If it goes several days,
we can recover observed sea surface heights from the `NOAA tides and water levels`_ .

:mod:`make_ssh_files` can take a date so that older files can be run.
Files from the observation site can also be run with the appropriate flag.

.. _NOAA forecast: https://nomads.ncep.noaa.gov/pub/data/nccf/com/etss/prod/

.. _NOAA tides and water levels: https://tidesandcurrents.noaa.gov/waterlevels.html?id=9443090


:py:mod:`download_weather` Worker Failure
=========================================

The Environment and Climate Change Canada (ECCC) 2.5 km resolution GEM forecast
model products from the High Resolution Deterministic Prediction System (HRDPS)
are critical inputs for the nowcast system.

The HRDPS products files that we use are downloaded every 6 hours via the
:py:mod:`nowcast.workers.collect_weather` worker.
If things are going really badly the
:py:mod:`~nowcast.workers.collect_weather` worker may not finish
hours after its expected completion time.
That can be determined by reading the `info log file`_ or `debug log file`_.

.. _info log file: https://salishsea.eos.ubc.ca/nemo/nowcast/logs/nowcast.log
.. _debug log file: https://salishsea.eos.ubc.ca/nemo/nowcast/logs/nowcast.debug.log

In the rare event that the nowcast automation system fails to download the HRDPS products,
it is critical that someone runs the :py:mod:`nowcast.workers.download_weather`
worker to download the files.
Confirm that the files exist on the
ECCC hpfx server by browsing the the date and forecast of interest;
e.g. ``https://hpfx.collab.science.gc.ca/yyyymmdd/WXO-DD/model_hrdps/continental/2.5km/hh/``,
where:

* ``yyyymmdd`` is the date of interest
* ``hh`` is the forecast name (00, 06, 12, or 18) of interest

then run the worker as follows:

#. :command:`ssh` on to ``skookum``,
   activate the production nowcast :program:`conda` environment,
   and navigate to the nowcast configuration and logging directory:

   .. code-block:: bash

       $ ssh skookum
       skookum$ conda activate /SalishSeaCast/nowcast-env

#. Run the :py:mod:`nowcast.workers.download_weather` worker
   for the appropriate forecast with debug logging,
   for example:

   .. code-block:: bash

       (/SalishSeaCast/nowcast-env)skookum$ python3 -m nowcast.workers.download_weather $NOWCAST_YAML 12 2.5km --debug

   The command above downloads the 12 forecast.
   The ``--debug`` flag causes the logging output of the worker to be displayed
   on the screen (so that you can see what is going on) instead of being written to a file.
   It also disconnects the worker from the nowcast messaging system so that there is
   no interaction with the manager and the ongoing automation.
   The (abridged) output should look like:

   .. code-block:: text

        2023-02-24 10:18:07,831 INFO [download_weather] running in process 3006
        2023-02-24 10:18:07,831 INFO [download_weather] read config from /SalishSeaCast/SalishSeaNowcast/config/nowcast.yaml
        2023-02-24 10:18:07,831 DEBUG [download_weather] **debug mode** no connection to manager
        2023-02-24 10:18:07,831 INFO [download_weather] downloading 12 2.5 km forecast GRIB2 files for 20230115
        2023-02-24 10:18:07,841 DEBUG [urllib3.connectionpool] Starting new HTTPS connection (1): hpfx.collab.science.gc.ca:443
        2023-02-24 10:18:08,112 DEBUG [urllib3.connectionpool] https://hpfx.collab.science.gc.ca:443 "GET /20230115/WXO-DD/model_hrdps/continental/2.5km/12/001/20230115T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT001H.grib2 HTTP/1.1" 200 1856503
        2023-02-24 10:18:10,748 DEBUG [download_weather] downloaded 1856503 bytes from https://hpfx.collab.science.gc.ca/20230115/WXO-DD/model_hrdps/continental/2.5km/12/001/20230115T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT001H.grib2
        2023-02-24 10:18:10,882 DEBUG [urllib3.connectionpool] https://hpfx.collab.science.gc.ca:443 "GET /20230115/WXO-DD/model_hrdps/continental/2.5km/12/001/20230115T12Z_MSC_HRDPS_VGRD_AGL-10m_RLatLon0.0225_PT001H.grib2 HTTP/1.1" 200 1823132
        2023-02-24 10:18:11,840 DEBUG [download_weather] downloaded 1823132 bytes from https://hpfx.collab.science.gc.ca/20230115/WXO-DD/model_hrdps/continental/2.5km/12/001/20230115T12Z_MSC_HRDPS_VGRD_AGL-10m_RLatLon0.0225_PT001H.grib2
        2023-02-24 10:18:12,135 DEBUG [urllib3.connectionpool] https://hpfx.collab.science.gc.ca:443 "GET /20230115/WXO-DD/model_hrdps/continental/2.5km/12/001/20230115T12Z_MSC_HRDPS_DSWRF_Sfc_RLatLon0.0225_PT001H.grib2 HTTP/1.1" 200 723914
        2023-02-24 10:18:13,021 DEBUG [download_weather] downloaded 723914 bytes from https://hpfx.collab.science.gc.ca/20230115/WXO-DD/model_hrdps/continental/2.5km/12/001/20230115T12Z_MSC_HRDPS_DSWRF_Sfc_RLatLon0.0225_PT001H.grib2
        2023-02-24 10:18:13,116 DEBUG [urllib3.connectionpool] https://hpfx.collab.science.gc.ca:443 "GET /20230115/WXO-DD/model_hrdps/continental/2.5km/12/001/20230115T12Z_MSC_HRDPS_DLWRF_Sfc_RLatLon0.0225_PT001H.grib2 HTTP/1.1" 200 2290020
        2023-02-24 10:18:14,277 DEBUG [download_weather] downloaded 2290020 bytes from https://hpfx.collab.science.gc.ca/20230115/WXO-DD/model_hrdps/continental/2.5km/12/001/20230115T12Z_MSC_HRDPS_DLWRF_Sfc_RLatLon0.0225_PT001H.grib2
        2023-02-24 10:18:14,371 DEBUG [urllib3.connectionpool] https://hpfx.collab.science.gc.ca:443 "GET /20230115/WXO-DD/model_hrdps/continental/2.5km/12/001/20230115T12Z_MSC_HRDPS_LHTFL_Sfc_RLatLon0.0225_PT001H.grib2 HTTP/1.1" 200 1314185
        2023-02-24 10:18:15,966 DEBUG [download_weather] downloaded 1314185 bytes from https://hpfx.collab.science.gc.ca/20230115/WXO-DD/model_hrdps/continental/2.5km/12/001/20230115T12Z_MSC_HRDPS_LHTFL_Sfc_RLatLon0.0225_PT001H.grib2

You can use the ``-h`` or ``--help`` flags to get a usage message that explains
the worker's required arguments,
and its option flags:

.. code-block:: bash

    (nowcast)$ python -m nowcast.workers.download_weather --help

.. code-block:: text

    usage: python -m nowcast.workers.download_weather [-h] [--debug] [--run-date RUN_DATE]
           [--no-verify-certs] config_file {12,06,00,18} {1km,2.5km}

    SalishSeaCast worker that downloads the GRIB2 files from the 00, 06, 12, or 18
    Environment and Climate Change Canada GEM 2.5km HRDPS operational model forecast.

    positional arguments:
      config_file          Path/name of YAML configuration file for NEMO nowcast.
      {12,06,00,18}        Name of forecast to download files from.
      {1km,2.5km}          Horizontal resolution of forecast to download files from.

    options:
      -h, --help           show this help message and exit
      --debug              Send logging output to the console instead of the log file,
                           and suppress messages to the nowcast manager process.
                           Nowcast system messages that would normally be sent to the
                           manager are logged to the console, suppressing interactions
                           with the manager such as launching other workers. Intended only
                           for use when the worker is run in foreground from the command-line.
      --run-date RUN_DATE  Forecast date to download. Use YYYY-MM-DD format.
                           Defaults to 2023-02-24.
      --no-verify-certs    Don't verify TLS/SSL certificates for downloads.
                           NOTE: This is intended for use *only* when downloading from
                           dd.alpha.meteo.gc.ca which has still uses deprecated TLS-1.0.

The ``--run-date`` flag allows you to download a prior date's forecast files.
To determine if the ``--run-date`` flag can be used check that the files exist on the
ECCC hpfx server by browsing the the date and forecast of interest;
e.g. ``https://hpfx.collab.science.gc.ca/yyyymmdd/WXO-DD/model_hrdps/continental/2.5km/hh/``,
where:

* ``yyyymmdd`` is the date of interest
* ``hh`` is the forecast name (00, 06, 12, or 18) of interest

Even if the worker cannot be re-run in the nowcast system deployment environment on
``skookum`` due to permission issues the forecast products can be downloaded using a
:ref:`SalishSeaNowcastDevelopmentEnvironment`.
That can be accomplished as follows:

#. Activate your nowcast :program:`conda` environment,
   and navigate to your nowcast development and testing environment:

   .. code-block:: bash

       $ source activate salishsea-nowcast
       (nowcast)$ cd MEOPAR/nowcast/

#. Edit the :file:`SalishSeaNowcast/config/nowcast.yaml` file to set a destination in your
   filespace for the GRIB2 files that the worker downloads:

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

#. Set the value of the :envvar:`NOWCAST_YAML` environment variable to the absolute path
   of the :file:`SalishSeaNowcast/config/nowcast.yaml` file that you edited.

#. Continue from step 2 above.
