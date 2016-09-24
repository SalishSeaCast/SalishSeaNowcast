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

.. _NOAA tides and water levels: http://tidesandcurrents.noaa.gov/waterlevels.html?id=9443090

.. _SSH_NeahBay: http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/nowcast/notebooks/SSH_NeahBay.ipynb


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

.. _info log file: eoas.ubc.ca/~dlatorne/MEOPAR/nowcast/nowcast.log
.. _debug log file: eoas.ubc.ca/~dlatorne/MEOPAR/nowcast/nowcast.debug.log

In the rare event that the nowcast automation system fails to download the HRDPS products every 6 hours via the :py:mod:`SalishSeaNowcast.nowcast.workers.download_weather` worker,
it is critical that someone re-run that worker.
That can be accomplished as follows:

#. :command:`ssh` on to :kbd:`skookum`,
   activate the production nowcast :program:`conda` environment,
   and navigate to the nowcast configuration and logging directory:

   .. code-block:: bash

       $ ssh skookum
       skookum$ source activate /results/nowcast-sys/nowcast-env
       (/results/nowcast-sys/nowcast-env)skookum$ cd /home/dlatorne/public_html/MEOPAR/nowcast/

   .. note::
      If :command:`source activate /results/nowcast-sys/nowcast-env` fails because it can't find :command:`activate`,
      you may be able to use:

      .. code-block:: bash

          skookum$ source /results/nowcast-sys/nowcast-env/bin/activate /results/nowcast-sys/nowcast-env

      as a work-around.

#. Run the :py:mod:`SalishSeaNowcast.nowcast.workers.download_weather` worker for the appropriate forecast with debug logging,
   for example:

   .. code-block:: bash

       (/results/nowcast-sys/nowcast-env)skookum$ python -m nowcast.workers.download_weather nowcast.yaml 12 --debug

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

Even if the worker cannot be re-run in the nowcast system deployment environment on :kbd:`skookum` due to permission issues the forecast products can be downloaded using a development and testing environment and directory structure as described above
(see :ref:`SalishSeaNowcastPythnonPackageEnvironmwnt` and :ref:`SalishSeaNowcastDirectoryStructure`).
That can be accomplished as follows:

#. Activate your nowcast :program:`conda` environment,
   and navigate to your nowcast development and testing environment:

   .. code-block:: bash

       $ source activate nowcast
       (nowcast)$ cd MEOPAR/nowcast/

#. Edit the :file:`MEOPAR/nowcast/nowcast.yaml` file to set a destination in your filespace for the GRIB2 files that the worker downloads:

   .. code-block:: yaml

       weather:
         # Destination directory for downloaded GEM 2.5km operational model GRIB2 files
         # GRIB_dir: /ocean/sallen/allen/research/MEOPAR/GRIB/
         GRIB_dir: /ocean/<your_userid>/MEOPAR/GRIB/

   .. note::

        The directory :file:`/ocean/<your_userid>/MEOPAR/GRIB/` must exist.
        Create it if necessary with:

        .. code-block:: bash

            $ mkdir -p /ocean/<your_userid>/MEOPAR/GRIB/

#. Continue from step 2 above.


Testing :kbd:`salishsea.eos.ubc.ca` Site Page Templates
-------------------------------------------------------

The pages that the nowcast automation maintains on the :kbd:`salishsea.eos.ubc.ca` site are generated from templates stored in :file:`MEOPAR/tools/SalishSeaNowcast/nowcast/www/templates/`.
Those templates are reStructuredText files that contain `Mako`_ directives that facilitate,
among other things,
substitution of concrete values (like specific dates) into placeholder variables,
and control structures like loops that simplify repetitive page elements (like collections of figure images),
and if-else blocks that allow conditional inclusion or exclusion of page elements.

.. _Mako: http://www.makotemplates.org/

So,
the process to get from a `Mako`_ page template to an HTML page happens in 2 stages:

#. Use a :py:class:`mako.template.Template` object derived from a :file:`.mako` file and a Python dict of placeholder variable names and values to render a :file:`.rst` file.

#. Use :command:`sphinx-build` to render the :file:`.rst` file to a :file:`.html` file.

In the nowcast production deployment the :file:`make_site_page.py` worker processes one or more page template(s) from the :file:`MEOPAR/tools/SalishSeaNowcast/nowcast/www/templates/` directory to create one or more :file:`.rst` file(s) in the :file:`MEOPAR/nowcast/www/salishsea-site/` directory tree.
When the :file:`make_site_page.py` worker sends a success message to the nowcast manager the :file:`push_to_web.py` worker is launched to:

#. Execute the :command:`hg update` command in :file:`MEOPAR/nowcast/www/salishsea-site/` to pull in any changes from other sources.

#. Execute the equivalent of :command:`make html` in the :file:`MEOPAR/nowcast/www/salishsea-site/site/` directory to run :command:`sphinx-build` to generate the new/changed pages of the site.

#. Execute an :command:`rsync` command to push the changes to the web server.

To test the rendering of site page templates we need to emulate the processing that the :file:`make_site_page.py` worker does and then run :command:`make html` in the :file:`MEOPAR/nowcast/www/salishsea-site/site/` directory so that we can preview the rendered page(s) from the :file:`MEOPAR/nowcast/www/salishsea-site/site/_build/html/` directory tree.

Since each page template contains a unique set of placeholder variables,
creating a general purpose template rendering test tool is probably more effort than it is worth.
Instead sample code that tests an early version of the template used to create the http://salishsea.eos.ubc.ca/storm-surge/forecast.html page is provided.
You can implement similar test code for other page templates in a Python script that you run from the command-line,
or in an IPython Notebook.

The template we're going to test looks like:

.. code-block:: mako

    ************************************************************************
    ${fcst_date.strftime('%A, %d %B %Y')} -- Salish Sea Storm Surge Forecast
    ************************************************************************

    Disclaimer
    ==========

    This site presents output from a research project.
    Results are not expected to be a robust prediction of the storm surge.


    Plots
    =====

    .. raw:: html
        <%
            run_dmy = run_date.strftime('%d%b%y').lower()
        %>
        %for svg_file in svg_file_roots:
        <object class="img-responsive" type="image/svg+xml"
          data="../_static/nemo/results_figures/forecast/${run_dmy}/${svg_file}_${run_dmy}.svg">
        </object>
        <hr>
        %endfor

    Model sea surface height has been evaluated through a series of hindcasts for significant surge events in 2006, 2009, and 2012 [1].

    [1] Soontiens, N., Allen, S., Latornell, D., Le Souef, K., Machuca, I., Paquin, J.-P., Lu, Y., Thompson, K., Korbel, V. (2015).  Storm surges in the Strait of Georgia simulated with a regional model. in prep.

The code below assumes that you are working in your :file:`MEOPAR/nowcast/` directory.

First some imports:

.. code-block:: python

    import datetime
    import os

    import mako.template

Create the template object from the :file:`.mako` file:

.. code-block:: python

    template_path = 'www/templates/'
    template_file = 'forecast.mako'
    mako_file = os.path.join(template_path, template_file)
    tmpl = mako.template.Template(filename=mako_file)

Now,
build the file name/path of the :file:`.rst` file that will be produces when we render the template:

.. code-block:: python

    site_path = 'www/salishsea-site/site/'
    page_path = 'storm-surge/'
    page_name = 'forecast.rst'
    rst_file = os.path.join(site_path, page_path, page_name)

Next,
calculate the template placeholder variables dict.
For this version of the forecast page we need the run date,
the forecast date,
and a list of figure image file name roots.

.. code-block:: python

    run_date = datetime.datetime.today()
    fcst_date = run_date + datetime.timedelta(days=1)
    vars = {
        'run_date': run_date,
        'fcst_date': fcst_date,
        'svg_file_roots': [
            'PA_tidal_predictions',
            'Vic_maxSSH',
            'PA_maxSSH',
            'CR_maxSSH',
            'NOAA_ssh',
            'WaterLevel_Thresholds',
            'SH_wind',
            'Avg_wind_vectors',
            'Wind_vectors_at_max',
        ],
    }

Finally,
use the :py:meth:`render` method of the template object to create the :file:`.rst` file:

.. code-block:: python

    with open(rst_file, 'wt') as f:
        f.write(tmpl.render(**vars))

Putting it all together:

.. code-block:: python

    import datetime
    import os

    import mako.template


    # Load the template
    template_path = 'www/templates/'
    template_file = 'forecast.mako'
    mako_file = os.path.join(template_path, template_file)
    tmpl = mako.template.Template(filename=mako_file)

    # Calculate the file path/name of the .rst file
    site_path = 'www/salishsea-site/site/'
    page_path = 'storm-surge/'
    page_name = 'forecast.rst'
    rst_file = os.path.join(site_path, page_path, page_name)

    # Calculate the template placeholder variable values
    run_date = datetime.datetime.today()
    fcst_date = run_date + datetime.timedelta(days=1)
    vars = {
        'run_date': run_date,
        'fcst_date': fcst_date,
        'svg_file_roots': [
            'PA_tidal_predictions',
            'Vic_maxSSH',
            'PA_maxSSH',
            'CR_maxSSH',
            'NOAA_ssh',
            'WaterLevel_Thresholds',
            'SH_wind',
            'Avg_wind_vectors',
            'Wind_vectors_at_max',
        ],
    }

    # Render the template
    with open(rst_file, 'wt') as f:
        f.write(tmpl.render(**vars))

Having executed the above code,
you should be able to go to :file:`MEOPAR/nowcast/www/salishsea-site/site/`,
execute :command:`make html`,
and preview the finished :file:`.html` page:

.. code-block:: bash

    (nowcast)$ cd MEOPAR/nowcast/www/salishsea-site/site/
    (nowcast)$ make html
    ...
    (nowcast)$ firefox _build/html/storm-surge/forecast.html
