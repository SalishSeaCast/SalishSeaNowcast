. Copyright 2013-2016 The Salish Sea MEOPAR contributors
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


.. _CreatingNowcastFigures:

Creating Nowcast Figures
========================

.. note::
    This is work-in-progress.

    The :py:mod:`nowcast.figures`,
    :py:mod:`nowcast.research_ferries`,
    and :py:mod:`nowcast.research_VENUS` modules are being refactored in the :kbd:`refactor-nowcast-figures` branch of the repo.

    The docs in this section reflect the organization of files and their contents that will result from that refactoring.

The web site figures that display the nowcast system run results are calculated by the :py:mod:`nowcast.workers.make_plots` worker using a collection of modules imported from :py:obj:`nowcast.figures`.
:py:obj:`nowcast.figures` is subdivided into 3 namespaces:

* :py:obj:`nowcast.figures.comparison`
* :py:obj:`nowcast.figures.publish`
* :py:obj:`nowcast.figures.research`

Within each of those namespaces the figure producing functions are organized into a module for each figure.
So,
for example,
the :py:mod:`nowcast.figures.comparison.salinity_ferry_route` module contains the code to produce a figure that compares salinity at 1.5m depth model results to
salinity observations from the ONC instrument package aboard a BC Ferries
vessel.

The code in the figure modules is just the code that is specific to creating that one figure.
Generic functions that are useful in the creation of multiple figures are collected in the modules of the :ref:`SalishSeaToolsPackage`.
For example,
:py:func:`salishsea_tools.viz_tools.set_aspect` is used to set the aspect ratio of a figure axes object appropriately for the Salish Sea NEMO model grid.
