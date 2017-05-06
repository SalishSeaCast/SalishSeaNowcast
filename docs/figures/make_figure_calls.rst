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

.. _CallingMakeFigureFunctionsInTheMakePlotsWorker:

***************************************************************************
Calling :py:func:`make_figure` Functions in the :py:mod:`make_plots` Worker
***************************************************************************

This section discusses:

* how to test a website figure module in a test notebook that replicates the nowcast system automation context
* how to add calls to a figure module's :py:func:`make_figure()` function to the :py:mod:`make_plots` nowcast system worker
* how to run the :py:mod:`make_plots` worker in debugging mode to test that it renders a figure correctly

You should run your test notebooks and :py:mod:`make_plots` worker tests in a :ref:`NowcastFiguresDevEnv`.
You can activate it with:

.. code-block:: bash

    $ source activate nowcast-fig-dev


.. _FigureModuleTestNotebook:

Figure Module Test Notebook
===========================

**To be written**


.. _MakePlotsWorkerCalls:

:py:mod:`make_plots` Worker Calls
=================================

**To be written**


.. _RunningMakePlotsWorkerToTestAFigure:

Running :py:mod:`make_plots` Worker to Test a Figure
====================================================

As a final test we'll run the :py:mod:`make_plots` worker in debug mode to test that it renders our figure correctly.

#. If you haven't done so already,
   activate your :ref:`NowcastFiguresDevEnv`,
   and navigate to your :file:`SalishSeaNowcast/` directory:

   .. code-block:: bash

       $ source activate nowcast-fig-dev
       (nowcast-fig-dev)$ cd SalishSeaNowcast/

#. Set up 2 environment variables that the nowcast system expectes to find:

   .. code-block:: bash

       (nowcast-fig-dev)$ export NOWCAST_LOGS=/tmp/
       (nowcast-fig-dev)$ export NOWCAST_ENV=$CONDA_PREFIX


#. Run the :py:mod:`make_plots` worker:

   .. code-block:: bash

       (nowcast-fig-dev)$ python -m nowcast.workers.make_plots config/nowcast.yaml nowcast-green research --debug --test-figure nitrate_thalweg_and_surface --run-date 2017-04-25

   **TODO:** Explain the command-line options

   The output of a successful test should look something like::

     2017-05-05 17:11:16,119 INFO [make_plots] running in process 2993
     2017-05-05 17:11:16,120 INFO [make_plots] read config from config/nowcast.yaml
     2017-05-05 17:11:16,120 DEBUG [make_plots] **debug mode** no connection to manager
     2017-05-05 17:11:16,358 DEBUG [make_plots] starting nowcast.figures.research.tracer_thalweg_and_surface.make_figure
     2017-05-05 17:11:18,645 INFO [make_plots] /results/nowcast-sys/figures/test/nowcast-green/25apr17/nitrate_thalweg_and_surface_25apr17.svg saved
     2017-05-05 17:11:18,646 INFO [make_plots] research plots for 2017-04-25 nowcast-green completed
     2017-05-05 17:11:18,647 DEBUG [make_plots] **debug mode** message that would have been sent to manager: (success nowcast-green research nowcast-green reseach plots produced)
     2017-05-05 17:11:18,647 DEBUG [make_plots] shutting down

   It is particularly important that your output contains the line that tells you that your figure was saved::

     INFO [make_plots] /results/nowcast-sys/figures/test/nowcast-green/25apr17/nitrate_thalweg_and_surface_25apr17.svg saved

   You can transform that path into a URL like::

     https://salishsea.eos.ubc.ca//test/nowcast-green/25apr17/nitrate_thalweg_and_surface_25apr17.svg

   and visually check your figure in your browser.

   Alternatively,
   you can use the :program:`Image Viewer` program on your workstation to open the file at that path.
