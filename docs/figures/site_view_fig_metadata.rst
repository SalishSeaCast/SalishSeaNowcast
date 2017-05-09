.. Copyright 2013-2017 The Salish Sea MEOPAR contributors
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

.. _SalishSeaCastWebPageViewFigureMetadata:

*******************************************
SalishSeaCast Web Page View Figure Metadata
*******************************************

This section discusses:

* how to add figure metadata to the :py:mod:`salishsea_site.views.salishseacast` module to make a figure appear on a web page
* how to run a local instance of the :kbd:`salishsea` website to confirm that the figure is on the web page

We'll use the :py:mod:`nowcast.figures.research.tracer_thalweg_and_surface` figure module as an example.

You should run your local :kbd:`salishsea` website server for testing in a :ref:`NowcastFiguresDevEnv`.
You can activate it with:

.. code-block:: bash

    $ source activate nowcast-fig-dev


.. _SalishseacastFigureMetadata:

:py:mod:`salishsea_site.views.salishseacast` Figure Metadata
============================================================

The `salishsea.eos.ubc.ca site web app`_ gathers figures that have been rendered by the nowcast system :py:mod:`make_plots` worker and presents them on web pages that are linked by date from the https://salishsea.eos.ubc.ca/nemo/results/ page.

.. _salishsea.eos.ubc.ca site web app: https://salishsea-site.readthedocs.io/en/latest/

Each row on the https://salishsea.eos.ubc.ca/nemo/results/ page contains links to pages that are generated from a page template by a view function in the :py:mod:`salishsea_site.views.salishseacast` module.
Each view function uses a list of :py:class:`salishsea_site.views.salishseacast.FigureMetadata` objects that is also defined in the :py:mod:`salishsea_site.views.salishseacast` module.
The :py:class:`~salishsea_site.views.salishseacast.FigureMetadata` objects set the title for the figure that will appear on the web page,
and the :kbd:`svg_name` of the figure files rendered by the :py:mod:`make_plots` worker.

So,
to add a figure rendered from our :py:mod:`nowcast.figures.research.tracer_thalweg_and_surface` figure module to the :guilabel:`Biology` page,
we add a :py:class:`~salishsea_site.views.salishseacast.FigureMetadata` object to the :py:obj:`~salishsea_site.views.salishseacast.biology_figures` list in the :py:mod:`salishsea_site.views.salishseacast` module:

.. code-block:: python

    FigureMetadata(
        title='Nitrate Fields Along Thalweg and on Surface',
        svg_name='nitrate_thalweg_and_surface',
    )

The value of the :kbd:`title` attribute appears in :guilabel:`Plots` list on the page as a link to the figure lower down on the page,
and it appears as a heading above the figure image.

The value of the :kbd:`svg_name` attribute is key that we used to register our figure function module in the :py:mod:`make_plots` worker.
Recall that the key is also used as the root part of the file name into which the figure is rendered.
That is:

* We registered a call to the :py:func:`nowcast.figures.research.tracer_thalweg_and_surface.make_figure` function in the :py:func:`nowcast.workers.make_plots._prep_nowcast_green_research_fig_functions` function using the key :kbd:`nitrate_thalweg_and_surface` to produce a nitrate thalweg and surface figure
* When the :py:mod:`make_plots` was run with the :kbd:`nowcast-green research --run-date 2017-04-29` it stored the rendered figure with the file name :file:`nitrate_thalweg_and_surface_29apr17.svg`

The order of :py:class:`~salishsea_site.views.salishseacast.FigureMetadata` objects in the :py:obj:`~salishsea_site.views.salishseacast.biology_figures` list determines the order in which the figures appear on the web page.


.. _TestingTheWebsiteView:

Testing the Website View
========================

#. If you haven't done so already,
   activate your :ref:`NowcastFiguresDevEnv`:

   .. code-block:: bash

       $ source activate nowcast-fig-dev\

#. Assuming that you have successfully run the :py:mod:`make_plots` worker :ref:`in test mode<RunningMakePlotsWorkerToTestAFigure>` for your figure,
   navigate to your :file:`SalishSeaNowcast/` directory,
   set up the 2 environment variables that the nowcast system expects to find,
   create a temporary logging directory for it to use:

   .. code-block:: bash

       (nowcast-fig-dev)$ export NOWCAST_LOGS=/tmp/$USER
       (nowcast-fig-dev)$ export NOWCAST_ENV=$CONDA_PREFIX
       (nowcast-fig-dev)$ mkdir -p $NOWCAST_LOGS

   and run the :py:mod:`make_plots` worker to render the figures of the type that you are working on for a recent date
   (like yesterday).
   For our test of the :py:mod:`nowcast.figures.research.tracer_thalweg_and_surface` figure module,
   the command would be like:

   .. code-block:: bash

       (nowcast-fig-dev)$ python -m nowcast.workers.make_plots config/nowcast.yaml nowcast-green research --debug --run-date 2017-05-07

#. Navigate to your :file:`salishsea-site/` directory,
   and launch the local website server with:

   .. code-block:: bash

       (nowcast-fig-dev)$ cd salishsea-site/
       (nowcast-fig-dev)$ pserve --reload development.ini

   You should see output like::

     Starting monitor for PID 10564.
     Starting server in PID 10564.
     serving on http://0.0.0.0:6543

   but the PID number will be different.
   The web server is now running in this terminal session.
   You can stop it with :kbd:`Ctrl-C` when you are finished.

#. Use your browser to navigate to http://localhost:6543/nemo/results/.
   From there you should be able to navigate to the page that will show you the figures
   for the date that you ran the :py:mod:`make_plots` worker for;
   for our test of the :py:mod:`nowcast.figures.research.tracer_thalweg_and_surface` figure module,
   that would be the :guilabel:`Biology` page.

#. If you need to edit the :py:class:`~salishsea_site.views.salishseacast.FigureMetadata` for your figure,
   the web server will restart automatically when you save the file so that you can see your changes by refreshing the page in your browser.
