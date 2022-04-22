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


.. _CallingMakeFigureFunctionsInTheMakePlotsWorker:

***************************************************************************
Calling :py:func:`make_figure` Functions in the :py:mod:`make_plots` Worker
***************************************************************************

This section discusses:

* how to test a website figure module in a test notebook that replicates the nowcast system automation context
* how to add calls to a figure module's :py:func:`make_figure` function to the :py:mod:`nowcast.workers.make_plots` nowcast system worker
* how to run the :py:mod:`~nowcast.workers.make_plots` worker in debugging mode to test that it renders a figure correctly

We'll use the :py:mod:`nowcast.figures.research.tracer_thalweg_and_surface` figure module as an example to create a nitrate thalweg and surface figure.

You should run your test notebooks and :py:mod:`~nowcast.workers.make_plots` worker tests in a :ref:`NowcastFiguresDevEnv`.
You can activate it with:

.. code-block:: bash

    $ source activate nowcast-fig-dev


.. _FigureModuleTestNotebook:

Figure Module Test Notebook
===========================

Once you've created a website figure module,
you should create a notebook that tests it in the nowcast context.
The `TestTracerThalwegAndSurfaceModule`_ notebook in :file:`notebooks/figures/research/` is an example for the :py:mod:`nowcast.figures.research.tracer_thalweg_and_surface` module.

.. _TestTracerThalwegAndSurfaceModule: https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/TestTracerThalwegAndSurface.ipynb


.. _RegisteringMakeFigureCallsInTheMakePlotsWorker:

Registering :py:func:`make_figure` Calls in the :py:mod:`make_plots` Worker
===========================================================================

Website figure modules like :py:mod:`nowcast.figures.research.tracer_thalweg_and_surface` produce :py:class:`matplotlib.figure.Figure` objects.
The :py:mod:`nowcast.workers.make_plots` worker is the element of the nowcast system automation that renders the :py:class:`~matplotlib.figure.Figure` objects to image files.
After a NEMO run has completed the :py:mod:`~nowcast.workers.make_plots` worker is launched to call the :py:func:`make_figure` functions that are registered for the run type.
The figure objects returned by the :py:func:`make_figure` functions are rendered to files in the :file:`/results/nowcast-sys/figures/` tree.
Files in that tree are served to the web by the nowcast system figure server.

The :py:mod:`~nowcast.workers.make_plots` worker organizes figures by NEMO run type and plot type.
The :command:`python -m nowcast.workers.make_plots -h` command will show you a list of the run types and plot types.
At present the run types are:

* :kbd:`nowcast`
* :kbd:`nowcast-green`
* :kbd:`forecast`
* :kbd:`forecast2`

and the plot types are:

* :kbd:`research`
* :kbd:`comparison`
* :kbd:`publish`

:py:mod:`~nowcast.workers.make_plots` also accepts a :kbd:`--run-date` to specify the date of the daily nowcast system NEMO run to create the figure for.
Without :kbd:`--run-date` today's date is used.

The :py:func:`~nowcast.workers.make_plots.make_plots` function uses paths defined in the nowcast system configuration file
(:file:`SalishSeaNowcast/config/nowcast.yaml`)
to set up a collection of commonly used paths and datasets such as:

* the results storage directory tree
* the weather forcing directory tree
* bathymetry and mesh mask files
* the BC and Washington coastline polygons file

Then :py:func:`~nowcast.workers.make_plots.make_plots` calls a :py:func:`_prep_*_fig_functions` function for the requested run type and plot type.
Those functions open the datasets that will be used to create the figure objects,
and return a data structure of information about the :py:func:`make_figure` calls that we want :py:mod:`~nowcast.workers.make_plots` to execute to render figures.
Adding an item to a :py:func:`_prep_*_fig_functions` function data structure is referred to as registering the :py:func:`make_figure` call.

To use the :py:mod:`nowcast.figures.research.tracer_thalweg_and_surface` to produce a figure that shows nitrate concentration on thalweg and surface slices we will register a call of its :py:func:`make_figure` function in the :py:func:`~nowcast.workers.make_plots._prep_nowcast_green_research_fig_functions` function:

.. code-block:: python

    def _prep_nowcast_green_research_fig_functions(bathy, mesh_mask, results_dir):
        ptrc_T_hr = _results_dataset('1h', 'ptrc_T', results_dir)
        fig_functions = {
            'nitrate_thalweg_and_surface': {
                'function': tracer_thalweg_and_surface.make_figure,
                'args': (ptrc_T_hr.variables['NO3'], bathy, mesh_mask),
                'kwargs': {'cmap': cmocean.cm.matter, 'depth_integrated': False}
            },
        }
        return fig_functions

That function presently loads only one results dataset,
from the hourly :kbd:`SalishSea_*_ptrc_T.nc` file from a :kbd:`nowcast-green` run.
If you wanted to also produce a salinity thalweg and surface figure you would need to add a line to load the corresponding :kbd:`grid_T.nc` dataset,
something like:

.. code-block:: python

    grid_T_hr = _results_dataset('1h', 'grid_T', results_dir)

Each :py:func:`make_figure` call that we want :py:mod:`~nowcast.workers.make_plots` is described by a :py:obj:`dict` item in the :py:obj:`fig_functions` dictionary:

.. code-block:: python

    'nitrate_thalweg_and_surface': {
        'function': tracer_thalweg_and_surface.make_figure,
        'args': (ptrc_T_hr.variables['NO3'], bathy, mesh_mask),
        'kwargs': {'cmap': cmocean.cm.matter, 'depth_integrated': False}
    }

The key,
:kbd:`nitrate_thalweg_and_surface` is the the root part of the file name into which the figure will be rendered.
If :py:mod:`~nowcast.workers.make_plots` is run with the command-line options :kbd:`nowcast-green research --run-date 2017-04-29`,
it will stored the rendered figure with the file name :file:`nitrate_thalweg_and_surface_29apr17.svg`.

The value is a :py:obj:`dict` that defines how to call the :py:func:`make_figure` function.
It has 2 required key/value pairs,
and 2 optional ones.

The :kbd:`function` key is required.
Its value is the name of the website figure module and the function in it to call (i.e. :py:func:`make_figure`) in dotted notation.
*Note that the value is a function object, so it is* **not** *enclosed in quotes.*
The website figure module must be imported at the top of the :py:mod:`~nowcast.workers.make_plots` module; e.g.

.. code-block:: python

    from nowcast.figures.research import tracer_thalweg_and_surface

The :kbd:`args` key is required.
Its value is is a :py:obj:`tuple` containing the positional arguments that :py:func:`make_figure` is to be called with.

The :kbd:`kwargs` key is optional.
Its value is a :py:obj:`dict` containing the keyword arguments and their values that :py:func:`make_plots` is to be called with.
If no keyword arguments are needed you can omit :kbd:`kwargs`.

The other optional key is :kbd:`format`.
Its value is the image format to use to store the rendered figure.
It defaults to :kbd:`svg`,
our preferred figure image format because it is a resolution-independent vector format.
The :kbd:`format` key is provided for the occassional special instances when we want to save images as :kbd:`png` bitmap images.

So,
the :py:obj:`fig_functions` item:

.. code-block:: python

    'nitrate_thalweg_and_surface': {
        'function': tracer_thalweg_and_surface.make_figure,
        'args': (ptrc_T_hr.variables['NO3'], bathy, mesh_mask),
        'kwargs': {'cmap': cmocean.cm.matter, 'depth_integrated': False}
    }

will result :py:mod:`~nowcast.workers.make_plots` doing the function call:

.. code-block:: python

    fig = tracer_thalweg_and_surface.make_figure(
        ptrc_T_hr.variables['NO3'], bathy, mesh_mask,
        cmap=cmocean.cm.matter, depth_integrated=False
    )

and storing the rendered :py:obj:`fig` in :file:`/results/nowcast-sys/figures/nowcast-green/ddmmmyy/nitrate_thalweg_and_surface_ddmmmyy.svg`.


.. _RunningMakePlotsWorkerToTestAFigure:

Running :py:mod:`make_plots` Worker to Test a Figure
====================================================

We can test that we have set up the necessary dataset loading and registered our :py:func:`make_figure` function correctly by running the :py:mod:`~nowcast.workers.make_plots` worker in debug mode to confirm that it renders our figure correctly.

#. If you haven't done so already,
   activate your :ref:`NowcastFiguresDevEnv`,
   and navigate to your :file:`SalishSeaNowcast/` directory:

   .. code-block:: bash

       $ source activate nowcast-fig-dev
       (nowcast-fig-dev)$ cd SalishSeaNowcast/

#. Set up 2 environment variables that the nowcast system expects to find,
   and create a temporary logging directory for it to use:

   .. code-block:: bash

       (nowcast-fig-dev)$ export NOWCAST_LOGS=/tmp/$USER
       (nowcast-fig-dev)$ export NOWCAST_ENV=$CONDA_PREFIX
       (nowcast-fig-dev)$ mkdir -p $NOWCAST_LOGS


#. Run the :py:mod:`make_plots` worker:

   .. code-block:: bash

       (nowcast-fig-dev)$ python -m nowcast.workers.make_plots config/nowcast.yaml nowcast-green research --debug --test-figure nitrate_thalweg_and_surface --run-date 2017-04-29

   The command line elements are:

   * :kbd:`-m` to tell Python to run a module
   * :kbd:`nowcast.workers.make_plots`, the module to run
   * :kbd:`config/nowcast.yaml` the path and file name of the nowcast system configuration file
   * :kbd:`nowcast-green`, the run type
   * :kbd:`research`, the plots type
   * :kbd:`--debug` to send logging output to the terminal and *not* communicate with the nowcast system manager process (**very important**)
   * :kbd:`--test-figure` to produce a test figure
   * :kbd:`nitrate_thalweg_and_surface` the key of the :py:func:`make_figure` call to test
   * :kbd:`--run-date` to say what date's run results to render the figure for

   The output of a successful test should look something like::

     2017-05-05 17:11:16,119 INFO [make_plots] running in process 2993
     2017-05-05 17:11:16,120 INFO [make_plots] read config from config/nowcast.yaml
     2017-05-05 17:11:16,120 DEBUG [make_plots] **debug mode** no connection to manager
     2017-05-05 17:11:16,358 DEBUG [make_plots] starting nowcast.figures.research.tracer_thalweg_and_surface.make_figure
     2017-05-05 17:11:18,645 INFO [make_plots] /results/nowcast-sys/figures/test/nowcast-green/29apr17/nitrate_thalweg_and_surface_29apr17.svg saved
     2017-05-05 17:11:18,646 INFO [make_plots] research plots for 2017-04-29 nowcast-green completed
     2017-05-05 17:11:18,647 DEBUG [make_plots] **debug mode** message that would have been sent to manager: (success nowcast-green research nowcast-green reseach plots produced)
     2017-05-05 17:11:18,647 DEBUG [make_plots] shutting down

   It is particularly important that your output contains the line that tells you that your figure was saved::

     INFO [make_plots] /results/nowcast-sys/figures/test/nowcast-green/29apr17/nitrate_thalweg_and_surface_29apr17.svg saved

   You can transform that path into a URL like::

     https://salishsea.eos.ubc.ca/test/nowcast-green/29apr17/nitrate_thalweg_and_surface_29apr17.svg

   and visually check your figure in your browser.

   Alternatively,
   you can use the :program:`Image Viewer` program on your workstation to open the file at that path.
