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
the :py:mod:`nowcast.figures.comparison.salinity_ferry_track` module contains the code to produce a figure that compares salinity at 1.5m depth model results to
salinity observations from the ONC instrument package aboard a BC Ferries
vessel.

The code in the figure modules is just the code that is specific to creating that one figure.
Generic functions that are useful in the creation of multiple figures are collected in the modules of the :ref:`SalishSeaToolsPackage`.
For example,
:py:func:`salishsea_tools.viz_tools.set_aspect` is used to set the aspect ratio of a figure axes object appropriately for the Salish Sea NEMO model grid.


.. _NowcastFigureExample:

An Example
----------

This section discusses the elements of a :py:obj:`nowcast.figures` module.
We'll use :py:mod:`~nowcast.figures.comparison.salinity_ferry_track` as the basis of the example.
The example focuses on the structure of the module and the functions it contains,
as well as the interfaces between those and the rest of the :ref:`SalishSeaNowcastPackage`.
In that spirit,
most of the actual implementation code is excluded from what follows.

First we'll show the module structure as a whole,
and then we'll look at each section in detail.

.. code-block:: python
    :linenos:

    # Copyright 2013-2016 The Salish Sea MEOPAR contributors
    # and The University of British Columbia

    # Licensed under the Apache License, Version 2.0 (the "License");
    # you may not use this file except in compliance with the License.
    # You may obtain a copy of the License at

    #    http://www.apache.org/licenses/LICENSE-2.0

    # Unless required by applicable law or agreed to in writing, software
    # distributed under the License is distributed on an "AS IS" BASIS,
    # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    # See the License for the specific language governing permissions and
    # limitations under the License.

    """Produce a figure that compares salinity at 1.5m depth model results to
    salinity observations from the ONC instrument package aboard a BC Ferries
    vessel.
    """
    from collections import namedtuple

    import matplotlib.pyplot as plt
    import numpy as np

    from salishsea_tools import (
        nc_tools,
        teos_tools,
        viz_tools,
    )

    import nowcast.figures.website_theme


    def salinity_ferry_track(
        grid_T_hr,
        figsize=(20, 7.5),
        theme=nowcast.figures.website_theme,
    ):
        """Plot salinity comparison of 1.5m depth model results to
        salinity observations from the ONC instrument package aboard a BC Ferries
        vessel as well as ferry route with model salinity distribution.

        :arg grid_T_hr:
        :type grid_T_hr: :py:class:`netCDF4.Dataset`

        :arg 2-tuple figsize: Figure size (width, height) in inches.

        :arg theme: Module-like object that defines the style elements for the
                    figure. See :py:mod:`nowcast.figures.website_theme` for an
                    example.

        :returns: :py:class:`matplotlib.figure.Figure`
        """
        lons, lats, sal_model, sal_obs = _prep_plot_data(grid_T_hr)
        fig, (ax_comp, ax_sal_map) = plt.subplots(
            1, 2, figsize=figsize, facecolor=theme.COLOURS['figure']['facecolor'])
        _plot_salinity_map(ax_sal_map, lons, lats, sal_model, sal_obs, theme)
        # _plot_salinity_comparison(ax_comp, sal_model, sal_obs, theme)
        return fig


    def _prep_plot_data(grid_T_hr):
        si, ei = 200, 610
        sj, ej = 20, 370
        lons = grid_T_hr.variables['nav_lon'][si:ei, sj:ej]
        lats = grid_T_hr.variables['nav_lat'][si:ei, sj:ej]
        model_depth_level = 1  # 1.5 m
        ## TODO: model time step for salinity contour map should be calculated from
        ##       ferry route time
        model_time_step = 3  # 02:30 UTC
        sal_hr = grid_T_hr.variables['vosaline']
        ## TODO: Use mesh mask instead of 0 for masking
        sal_masked = np.ma.masked_values(
            sal_hr[model_time_step, model_depth_level, si:ei, sj:ej], 0)
        timestamped_sal = namedtuple('timestamped_sal', 'salinity, timestamp')
        sal_model = timestamped_sal(
            teos_tools.psu_teos(sal_masked),
            nc_tools.timestamp(grid_T_hr, model_time_step))
        return lons, lats, sal_model, None


    def _plot_salinity_map(ax, lons, lats, sal_model, sal_obs, theme):
      ax.set_axis_bgcolor(theme.COLOURS['contour mesh']['land'])
      cmap = plt.get_cmap('plasma')
      contour_levels = 20
      mesh = ax.contourf(
          lons, lats, sal_model.salinity, contour_levels, cmap=cmap)
      cbar = plt.colorbar(mesh, ax=ax, shrink=0.965)
      # Plot ferry track
      ## TODO: Handle sal_obs data structure
      # ax.plot(sal_obs, color='black', linewidth=4)
      _salinity_map_place_markers(ax, theme)
      # Format the axes and make it pretty
      _salinity_map_axis_labels(ax, sal_model, theme)
      _salinity_map_cbar_labels(cbar, theme)
      _salinity_map_set_view(ax, lats)


    def _salinity_map_place_markers(ax, theme):
      ...


    def _salinity_map_axis_labels(ax, sal_model, theme):
      ...


    def _salinity_map_cbar_labels(cbar, theme):
      ...


    def _salinity_map_set_view(ax, lats):
      ...


    def _plot_salinity_comparison(ax, sal_model, sal_obs, theme):
      # plot observations for ferry crossing
      # plot model results from time steps that "bracket" observations
      # Format the axes and make it pretty
      _salinity_comparison_axis_labels(ax, theme)
      _salinity_comparison_set_view(ax)


    def _salinity_comparison_axis_labels(ax, theme):
      ...


    def _salinity_comparison_set_view(ax):
      ...


Copyright Notice
^^^^^^^^^^^^^^^^

Lines 1-14 are our :ref:`LibraryCodeStandardCopyrightHeaderBlock`:

.. code-block:: python
    :linenos:
    :lineno-start: 1

    # Copyright 2013-2016 The Salish Sea MEOPAR contributors
    # and The University of British Columbia

    # Licensed under the Apache License, Version 2.0 (the "License");
    # you may not use this file except in compliance with the License.
    # You may obtain a copy of the License at

    #    http://www.apache.org/licenses/LICENSE-2.0

    # Unless required by applicable law or agreed to in writing, software
    # distributed under the License is distributed on an "AS IS" BASIS,
    # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    # See the License for the specific language governing permissions and
    # limitations under the License.


Module Docstring
^^^^^^^^^^^^^^^^

Lines 16-19 is the module docstring.
It will appear at top of the :ref:`LibraryCodeAutoGeneratedDocs`
(:py:mod:`nowcast.figures.comparison.salinity_ferry_track` in this case).

.. code-block:: python
    :linenos:
    :lineno-start: 16

    """Produce a figure that compares salinity at 1.5m depth model results to
    salinity observations from the ONC instrument package aboard a BC Ferries
    vessel.
    """


Imports
^^^^^^^

Next come the imports
(lines 20-31 in our example):

.. code-block:: python
    :linenos:
    :lineno-start: 20

    from collections import namedtuple

    import matplotlib.pyplot as plt
    import numpy as np

    from salishsea_tools import (
        nc_tools,
        teos_tools,
        viz_tools,
    )

    import nowcast.figures.website_theme

The Python standard library imports,
those from 3rd party libraries like :py:obj:`matplotlib`,
:py:obj:`numpy`,
etc.,
and imports from the :ref:`SalishSeaToolsPackage` will vary from one figure module to another.
However,
the

.. code-block:: python

    import nowcast.figures.website_theme

import must be present in every figure module.
:py:mod:`nowcast.figures.website_theme` provides the definition of colours and fonts that figure modules must use in order to ensure consistency from one to the next,
and with the :kbd:`salishsea.eos.ubc.ca` site NEMO results section styling.

See :ref:`nowcast.figures.website_theme` for more details about the :py:mod:`~nowcast.figures.website_theme` module.

See :ref:`library code Imports <LibraryCodeImports>` section for notes on organizing imports,
coding style,
and other guidelines.


Figure Creation Function
^^^^^^^^^^^^^^^^^^^^^^^^

The first function in the module is the function that will be called by the :py:mod:`nowcast.workers.make_plots` worker to return a :py:class:`matplotlib.figure.Figure` object.
This function has the same name as the module.
It is also the module's only :ref:`public function <LibraryCodePublicAndPrivate>` function.

.. code-block:: python
    :linenos:
    :lineno-start: 34

    def salinity_ferry_track(
        grid_T_hr,
        figsize=(20, 7.5),
        theme=nowcast.figures.website_theme,
    ):
        """Plot salinity comparison of 1.5m depth model results to
        salinity observations from the ONC instrument package aboard a BC Ferries
        vessel as well as ferry route with model salinity distribution.

        :arg grid_T_hr:
        :type grid_T_hr: :py:class:`netCDF4.Dataset`

        :arg 2-tuple figsize: Figure size (width, height) in inches.

        :arg theme: Module-like object that defines the style elements for the
                    figure. See :py:mod:`nowcast.figures.website_theme` for an
                    example.

        :returns: :py:class:`matplotlib.figure.Figure`
        """
        lons, lats, sal_model, sal_obs = _prep_plot_data(grid_T_hr)
        fig, (ax_comp, ax_sal_map) = plt.subplots(
            1, 2, figsize=figsize, facecolor=theme.COLOURS['figure']['facecolor'])
        _plot_salinity_map(ax_sal_map, lons, lats, sal_model, sal_obs, theme)
        _plot_salinity_comparison(ax_comp, sal_model, sal_obs, theme)
        return fig

The function signature
(lines 34-38)
...

The function docstring
(lines 39-53)
...

The function code does 4 things:

1. Call a module-private function :py:func:`_prep_plot_data` to prepare the collection of objects that contain the data that will be plotted in the figure
   (line 54).

2. Call :py:func:`matplotlib.pyplot.subplots` or a module-private function :py:func:`_prep_fig_axes`
   (lines 55-56).
   In either case,
   those functions return:

   * a :py:obj:`matplotlib.figure.Figure` object
   * a collection of one or more :py:obj:`matplotlib.axes.Axes` objects,
     one for each axes in the figure

   The :py:func:`matplotlib.pyplot.subplots` and :py:func:`_prep_fig_axes` functions accept keyword arguments named :kbd:`figsize` and :kbd:`facecolor` to set the size and shape of the figure area,
   and its background colour as defined in the :py:mod:`nowcast.figures.website_theme` :ref:`WebsiteTheme` module by :py:attr:`COLOURS['figure']['facecolor']`.

   A :py:func:`_prep_fig_axes` function would be used :py:class:`matplotlib.gridspec.Gridspec` is used to define more complex layout of axes than can be provided by :py:func:`matplotlib.pyplot.subplots`.

3. For each axes object returned by :py:func:`matplotlib.pyplot.subplots` or :py:func:`_prep_fig_axes`,
   call a module-private function whose name starts with :py:func:`_plot_` to draw all the things on the axes
   (lines 57 and 58).

4. Return the :py:obj:`matplotlib.figure.Figure` object to the :py:mod:`nowcast.workers.make_plots` worker.


Automatic Module Documentation Generation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When you create a new figure module don't forget to add it to the :file:`tools/SalishSeaNowcast/docs/api.rst` file so that API documentation will be generated for it.
For our example,
the content added to :file:`tools/SalishSeaNowcast/docs/api.rst` is:

.. code-block:: restructuredtext

    .. _nowcast.figures.comparison.salinity_ferry_track:

    :py:mod:`nowcast.figures.comparison.salinity_ferry_track` Module
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    .. automodule:: nowcast.figures.comparison.salinity_ferry_track
        :members:



.. _WebsiteTheme:

Website Theme
-------------

TODO
