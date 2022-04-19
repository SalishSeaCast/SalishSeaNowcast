..  Copyright 2013 – present The Salish Sea MEOPAR contributors
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

.. _CreatingAFigureModule:

************************
Creating a Figure Module
************************

This section discusses the elements of a :py:obj:`nowcast.figures` module.
We'll use :py:mod:`nowcast.figures.research.tracer_thalweg_and_surface` as the basis of the example.
The example focuses on the structure of the module and the functions it contains,
as well as the interfaces between those and the rest of the :ref:`SalishSeaNowcastPackage`.

There are some very strong opinions in this section about what function names to use,
and how to break the code that creates a figure up into functions.
They are here because we have learned the hard way that figure generation code quickly evolves into hard to read and maintain globs with fragile interconnections.
Please follow the methodology in this section,
but do feel free to discuss it with the group so that we can try to improve.

The `DevelopTracerThalwegAndSurfaceModule`_ notebook in :file:`notebooks/figures/research/` was used to develop our example figure module's functions.
You can take that approach if you wish,
or you can develop directly in a module.

.. _DevelopTracerThalwegAndSurfaceModule: https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/DevelopTracerThalwegAndSurfaceModule.ipynb

Of course,
the ultimate goal is to produce a module.
Once you've got a code module,
you should create a notebook that tests it in the nowcast context.
The `TestTracerThalwegAndSurfaceModule`_ notebook in :file:`notebooks/figures/research/` is an example for the :py:mod:`nowcast.figures.research.tracer_thalweg_and_surface` module.

.. _TestTracerThalwegAndSurfaceModule: https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/TestTracerThalwegAndSurface.ipynb


Example Module
==============

First we'll show the :py:mod:`~nowcast.figures.research.tracer_thalweg_and_surface` module structure as a whole,
and then we'll look at each section in detail.

.. code-block:: python

    # Copyright 2013 – present The Salish Sea MEOPAR contributors
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

    """Produce a figure that shows colour contours of a tracer on a vertical slice
    along a section of the domain thalweg,
    and on the surface for a section of the domain that excludes Puget Sound
    in the south and Johnstone Strait in the north.
    """
    from types import SimpleNamespace

    import matplotlib.pyplot as plt
    from matplotlib import gridspec
    import numpy as np

    from salishsea_tools import visualisations as vis
    from salishsea_tools import viz_tools

    import nowcast.figures.website_theme


    def make_figure(
        tracer_var, bathy, mesh_mask, cmap, depth_integrated,
        figsize=(16, 9), theme=nowcast.figures.website_theme
    ):
        """Plot colour contours of tracer on a vertical slice along a section of
        the domain thalweg,
        and on the surface for the Strait of Georgia and Juan de Fuca Strait
        regions of the domain.

        :param tracer_var: Hourly average tracer results from NEMO run.
        :type tracer_var: :py:class:`netCDF4.Variable`

        :param bathy: Salish Sea NEMO model bathymetry data.
        :type bathy: :class:`netCDF4.Dataset`

        :param mesh_mask: NEMO-generated mesh mask for run that produced tracer_var.
        :type mesh_mask: :class:`netCDF4.Dataset`

        :param cmap: Colour map to use for tracer_var contour plots.
        :type cmap: :py:class:`matplotlib.colors.LinearSegmentedColormap`

        :param boolean depth_integrated: Integrate the tracer over the water column
                                         depth when :py:obj:`True`.

        :param 2-tuple figsize: Figure size (width, height) in inches.

        :param theme: Module-like object that defines the style elements for the
                    figure. See :py:mod:`nowcast.figures.website_theme` for an
                    example.

        :returns: :py:class:`matplotlib.figure.Figure`
        """
        plot_data = _prep_plot_data(tracer_var, mesh_mask, depth_integrated)
        fig, (ax_thalweg, ax_surface) = _prep_fig_axes(figsize, theme)

        clevels_thalweg, clevels_surface, show_thalweg_cbar = _calc_clevels(
            plot_data)

        cbar_thalweg = _plot_tracer_thalweg(
            ax_thalweg, plot_data, bathy, mesh_mask, cmap, clevels_thalweg)
        _thalweg_axes_labels(
            ax_thalweg, plot_data, show_thalweg_cbar, clevels_thalweg,
            cbar_thalweg, theme)

        cbar_surface = _plot_tracer_surface(
            ax_surface, plot_data, cmap, clevels_surface)
        _surface_axes_labels(
            ax_surface, tracer_var, depth_integrated, clevels_surface, cbar_surface,
            theme)
        return fig


    def _prep_plot_data(tracer_var, mesh_mask, depth_integrated):
        hr = 19
        sj, ej = 200, 800
        si, ei = 20, 395

        tracer_hr = tracer_var[hr]
        masked_tracer_hr = np.ma.masked_where(
            mesh_mask['tmask'][0, ...] == 0, tracer_hr)
        surface_hr = masked_tracer_hr[0, sj:ej, si:ei]

        if depth_integrated:
            grid_heights = mesh_mask.variables['e3t_1d'][:][0].reshape(
                tracer_hr.shape[0], 1, 1)
            height_weighted = masked_tracer_hr[:, sj:ej, si:ei] * grid_heights
            surface_hr = height_weighted.sum(axis=0)

        return SimpleNamespace(
            tracer_var=tracer_var,
            tracer_hr=tracer_hr,
            surface_hr=surface_hr,
            surface_j_limits=(sj, ej),
            surface_i_limits=(si, ei),
            thalweg_depth_limits=(0, 450),
            thalweg_length_limits=(0, 632),
        )


    def _prep_fig_axes(figsize, theme):
        fig = plt.figure(
            figsize=figsize, facecolor=theme.COLOURS['figure']['facecolor'])

        gs = gridspec.GridSpec(1, 2, width_ratios=[1.618, 1])

        ax_thalweg = fig.add_subplot(gs[0])
        ax_thalweg.set_axis_bgcolor(theme.COLOURS['axes']['background'])

        ax_surface = fig.add_subplot(gs[1])
        ax_surface.set_axis_bgcolor(theme.COLOURS['axes']['background'])

        return fig, (ax_thalweg, ax_surface)


    def _calc_clevels(plot_data):
        """Calculates contour levels for the two axes and decides whether whether
        the levels are similar enough that one colour bar is sufficient for the
        figure, or if each axes requires one.
        """
        percent_98_surf = np.percentile(plot_data.surface_hr.compressed(), 98)
        percent_2_surf = np.percentile(plot_data.surface_hr.compressed(), 2)

        percent_98_grid = np.percentile(
            np.ma.masked_values(plot_data.tracer_hr, 0).compressed(), 98)
        percent_2_grid = np.percentile(
            np.ma.masked_values(plot_data.tracer_hr, 0).compressed(), 2)

        overlap = (
            max(0, min(percent_98_surf, percent_98_grid)
                - max(percent_2_surf, percent_2_grid)))
        magnitude = (
            (percent_98_surf - percent_2_surf) + (percent_98_grid - percent_2_grid))
        if 2 * overlap / magnitude > 0.5:
            max_clevel = max(percent_98_surf, percent_98_grid)
            min_clevel = min(percent_2_surf, percent_2_grid)
            clevels_thalweg = np.arange(
                min_clevel, max_clevel, (max_clevel - min_clevel) / 20.0)
            clevels_surface = clevels_thalweg
            show_thalweg_cbar = False
        else:
            clevels_thalweg = np.arange(
                percent_2_grid, percent_98_grid,
                (percent_98_grid - percent_2_grid) / 20.0)
            clevels_surface = np.arange(
                percent_2_surf, percent_98_surf,
                (percent_98_surf - percent_2_surf) / 20.0)
            show_thalweg_cbar = True
        return clevels_thalweg, clevels_surface, show_thalweg_cbar


    def _plot_tracer_thalweg(ax, plot_data, bathy, mesh_mask, cmap, clevels):
        cbar = vis.contour_thalweg(
            ax, plot_data.tracer_hr, bathy, mesh_mask, clevels=clevels, cmap=cmap,
            thalweg_file='/SalishSeaCast/tools/bathymetry/thalweg_working.txt',
            cbar_args={'fraction': 0.030, 'pad': 0.04, 'aspect': 45}
        )
        return cbar


    def _thalweg_axes_labels(
        ax, plot_data, show_thalweg_cbar, clevels, cbar, theme
    ):
        ax.set_xlim(plot_data.thalweg_length_limits)
        ax.set_ylim(
            plot_data.thalweg_depth_limits[1], plot_data.thalweg_depth_limits[0])
        if show_thalweg_cbar:
            label = (
                f'{plot_data.tracer_var.long_name} [{plot_data.tracer_var.units}]')
            _cbar_labels(cbar, clevels[::2], theme, label)
        else:
            cbar.remove()
        ax.set_xlabel(
            'Distance along thalweg [km]', color=theme.COLOURS['text']['axis'],
            fontproperties=theme.FONTS['axis'])
        ax.set_ylabel(
            'Depth [m]', color=theme.COLOURS['text']['axis'],
            fontproperties=theme.FONTS['axis'])
        theme.set_axis_colors(ax)


    def _cbar_labels(cbar, contour_intervals, theme, label):
        cbar.set_ticks(contour_intervals)
        cbar.ax.axes.tick_params(labelcolor=theme.COLOURS['cbar']['tick labels'])
        cbar.set_label(
            label,
            fontproperties=theme.FONTS['axis'],
            color=theme.COLOURS['text']['axis'])


    def _plot_tracer_surface(ax, plot_data, cmap, clevels):
        x, y = np.meshgrid(
            np.arange(*plot_data.surface_i_limits, dtype=int),
            np.arange(*plot_data.surface_j_limits, dtype=int))
        mesh = ax.contourf(
            x, y, plot_data.surface_hr, levels=clevels, cmap=cmap, extend='both')
        cbar = plt.colorbar(mesh, ax=ax, fraction=0.034, pad=0.04, aspect=45)
        return cbar


    def _surface_axes_labels(
        ax, tracer_var, depth_integrated, clevels, cbar, theme
    ):
        cbar_units = (
            f'{tracer_var.units}*m' if depth_integrated
            else f'{tracer_var.units}')
        cbar_label = f'{tracer_var.long_name} [{cbar_units}]'
        _cbar_labels(cbar, clevels[::2], theme, cbar_label)
        ax.set_xlabel(
            'Grid x', color=theme.COLOURS['text']['axis'],
            fontproperties=theme.FONTS['axis'])
        ax.set_ylabel(
            'Grid y', color=theme.COLOURS['text']['axis'],
            fontproperties=theme.FONTS['axis'])
        ax.set_axis_bgcolor('burlywood')
        viz_tools.set_aspect(ax)
        theme.set_axis_colors(ax)

.. note::

    Line numbers beside the code fragments in this section would be a definite improvement.
    Unfortunately they are badly misaligned in the :kbd:`sphinx_rtd_theme` presently deployed on readthedocs.org (v0.1.7).
    That bug is fixed in v0.1.9,
    broken again somewhere between that version and v0.2.4,
    and fixed again in v0.2.5b1.
    Until readthedocs.org updates their deployed version,
    or allows us to specify the version,
    we're stuck without line numbers.
    Sorry.


Summary of Functions in a Figure Module
=======================================

The function that the :py:mod:`nowcast.workers.make_plots` worker will call is named :py:func:`make_figure`.
More details in :ref:`MakeFigureFunction` section.

:py:func:`make_figure` starts by calling 2 other functions:

#. :py:func:`_prep_plot_data` to do all of the extraction and preparatory processing of the data that will be plotted in the figure's axes objects.
    All of the slicing of the plot data from the dataset objects passed into the ::py:func:`make_figure`,
    and any calculations that are required should be done in :py:func:`_prep_plot_data` so that the variables it returns are ready to be passed into plotting methods.
    More details in the :ref:`PrepPlotDataFunction` section.

#. :py:func:`_prep_fig_axes` creates the figure and axes objects that the variables will be plotted on.
   More details in the :ref:`PrepFixAxesFunction` section.

:py:func:`make_figure` then calls a function whose name starts with :py:func:`_plot_` for each of the axes objects returned by :py:func:`_prep_fig_axes`.

If the processing in the :py:func:`_prep_plot_data`,
:py:func:`_prep_fig_axes`,
or :py:func:`_plot_*` functions is long or complicated,
it may be broken up into additional functions that those functions call.
Examples include:

* Code that is used to prepare several variables like the :py:func:`nowcast.figures.comparison.compare_venus_ctd._calc_results_time_series` function

* Axis labeling and prettifying code like :py:func:`nowcast.figures.research.tracer_thalweg_and_surface._thalweg_axes_labels`

* Code to calculate contour levels like :py:func:`nowcast.figures.research.tracer_thalweg_and_surface._calc_clevels`

The following sub-sections go through the example module above section by section to discuss its details.


Copyright Notice
================

At the top of the file is our :ref:`LibraryCodeStandardCopyrightHeaderBlock`:

.. code-block:: python

    # Copyright 2013 – present The Salish Sea MEOPAR contributors
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
================

The module docstring will appear at top of the :ref:`automatically generated module documentation <LibraryCodeAutoGeneratedDocs>`
(:py:mod:`nowcast.figures.research.tracer_thalweg_and_surface` in this case).

.. code-block:: python

    """Produce a figure that shows colour contours of a tracer on a vertical slice
    along a section of the domain thalweg,
    and on the surface for a section of the domain that excludes Puget Sound
    in the south and Johnstone Strait in the north.
    """


Imports
=======

Next come the imports:

.. code-block:: python

    from types import SimpleNamespace

    import matplotlib.pyplot as plt
    from matplotlib import gridspec
    import numpy as np

    from salishsea_tools import visualisations as vis
    from salishsea_tools import viz_tools

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


.. _MakeFigureFunction:

:py:func:`make_figure` Function
===============================

The first function in the module is the function that will be called by the :py:mod:`nowcast.workers.make_plots` worker to return a :py:class:`matplotlib.figure.Figure` object.
This function is always named :py:func:`make_figure()`.
It is also the module's only :ref:`public function <LibraryCodePublicAndPrivate>`.

.. code-block:: python

    def make_figure(
        tracer_var, bathy, mesh_mask, cmap, depth_integrated,
        figsize=(16, 9), theme=nowcast.figures.website_theme
    ):
        """Plot colour contours of tracer on a vertical slice along a section of
        the domain thalweg,
        and on the surface for the Strait of Georgia and Juan de Fuca Strait
        regions of the domain.

        :param tracer_var: Hourly average tracer results from NEMO run.
        :type tracer_var: :py:class:`netCDF4.Variable`

        :param bathy: Salish Sea NEMO model bathymetry data.
        :type bathy: :class:`netCDF4.Dataset`

        :param mesh_mask: NEMO-generated mesh mask for run that produced tracer_var.
        :type mesh_mask: :class:`netCDF4.Dataset`

        :param cmap: Colour map to use for tracer_var contour plots.
        :type cmap: :py:class:`matplotlib.colors.LinearSegmentedColormap`

        :param boolean depth_integrated: Integrate the tracer over the water column
                                         depth when :py:obj:`True`.

        :param 2-tuple figsize: Figure size (width, height) in inches.

        :param theme: Module-like object that defines the style elements for the
                    figure. See :py:mod:`nowcast.figures.website_theme` for an
                    example.

        :returns: :py:class:`matplotlib.figure.Figure`
        """
        plot_data = _prep_plot_data(tracer_var, mesh_mask, depth_integrated)
        fig, (ax_thalweg, ax_surface) = _prep_fig_axes(figsize, theme)

        clevels_thalweg, clevels_surface, show_thalweg_cbar = _calc_clevels(
            plot_data)

        cbar_thalweg = _plot_tracer_thalweg(
            ax_thalweg, plot_data, bathy, mesh_mask, cmap, clevels_thalweg)
        _thalweg_axes_labels(
            ax_thalweg, plot_data, show_thalweg_cbar, clevels_thalweg,
            cbar_thalweg, theme)

        cbar_surface = _plot_tracer_surface(
            ax_surface, plot_data, cmap, clevels_surface)
        _surface_axes_labels(
            ax_surface, tracer_var, depth_integrated, clevels_surface, cbar_surface,
            theme)
        return fig


Function Signature
------------------

The function signature

.. code-block:: python

    def make_figure(
        tracer_var, bathy, mesh_mask, cmap, depth_integrated,
        figsize=(16, 9), theme=nowcast.figures.website_theme
    ):


should use model results dataset objects rather than file names so that the datasets are loaded once by the :py:mod:`nowcast.workers.make_plots` worker and references to them passed into the figure creation functions.

The signature ends with the default-values keyword arguments :kbd:`figsize` and :kbd:`theme`.

The :kbd:`figsize` 2-tuple give the width and height of the figure,
but more importantly its aspect ratio.
Choose values that are appropriate to the information presented in the figure.
If you don't have a good reason to choose something else,
use :kbd:`figsize=(16, 9)` because that matches the aspect ration of wide displays that most people use to view web sites
(even phones in landscape orientation).

The :kbd:`theme` should be defaulted to :py:mod:`nowcast.figures.website_theme`, a module that provides colours and font specifications that fit with the `salishsea site`_ colour scheme and provide consistency among the figures.

.. _salishsea site: https://salishsea.eos.ubc.ca


Function Docstring
------------------

The function docstring

.. code-block:: python

    """Plot colour contours of tracer on a vertical slice along a section of
    the domain thalweg,
    and on the surface for the Strait of Georgia and Juan de Fuca Strait
    regions of the domain.

    :param tracer_var: Hourly average tracer results from NEMO run.
    :type tracer_var: :py:class:`netCDF4.Variable`

    :param bathy: Salish Sea NEMO model bathymetry data.
    :type bathy: :class:`netCDF4.Dataset`

    :param mesh_mask: NEMO-generated mesh mask for run that produced tracer_var.
    :type mesh_mask: :class:`netCDF4.Dataset`

    :param cmap: Colour map to use for tracer_var contour plots.
    :type cmap: :py:class:`matplotlib.colors.LinearSegmentedColormap`

    :param boolean depth_integrated: Integrate the tracer over the water column
                                     depth when :py:obj:`True`.

    :param 2-tuple figsize: Figure size (width, height) in inches.

    :param theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """

includes description and type information for each of the function arguments.
Those are written using `Sphinx Info Field List markup`_ so that they render nicely in the :ref:`automatically generated module documentation <AutomaticModuleDocumentationGeneration>`.

.. _Sphinx Info Field List markup: https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html#info-field-lists

Simple,
1-word type information can be included in the :kbd:`:param ...:` role,
for example:

.. code-block:: restructuredtext

    :param boolean depth_integrated: Integrate the tracer over the water column
                                     depth when :py:obj:`True`.

More complicated type information should go in a separate :kbd:`:type ...:` role like:

.. code-block:: restructuredtext

    :param tracer_var: Hourly average tracer results from NEMO run.
    :type tracer_var: :py:class:`netCDF4.Variable`


Function Code
-------------

The function code does 4 things:

1. Call a module-private function :py:func:`_prep_plot_data` to prepare the collection of objects that contain the data that will be plotted in the figure:

    .. code-block:: python

        plot_data = _prep_plot_data(tracer_var, mesh_mask, depth_integrated)

2. Call a module-private function :py:func:`_prep_fig_axes`:

    .. code-block:: python

        fig, (ax_thalweg, ax_surface) = _prep_fig_axes(figsize, theme)

   That function returns:

   * a :py:class:`matplotlib.figure.Figure` object
   * a tuple of :py:class:`matplotlib.axes.Axes` objects,
     one for each axes in the figure

   The :py:func:`_prep_fig_axes` function accept arguments named :kbd:`figsize` and :kbd:`theme`.
   :kbd:`figsize` provides the size and shape of the figure area.
   :kbd:`theme` provides the :py:mod:`nowcast.figures.website_theme` :ref:`WebsiteTheme` module which defines things like the figure and axes background colours.

   The tuple of axes objects returned by :py:func:`_prep_fig_axes` should be given meaningful names as shown above rather than:

   .. code-block:: python

        fig, (ax1, ax2, ax2, ax4) = _prep_fig_axes(figsize, theme)

3. For each axes object returned by :py:func:`_prep_fig_axes`,
   call a module-private function whose name starts with :py:func:`_plot_` is called to draw all the things on the axes:

    .. code-block:: python

        clevels_thalweg, clevels_surface, show_thalweg_cbar = _calc_clevels(
            plot_data)

        cbar_thalweg = _plot_tracer_thalweg(
            ax_thalweg, plot_data, bathy, mesh_mask, cmap, clevels_thalweg)
        _thalweg_axes_labels(
            ax_thalweg, plot_data, show_thalweg_cbar, clevels_thalweg,
            cbar_thalweg, theme)

        cbar_surface = _plot_tracer_surface(
            ax_surface, plot_data, cmap, clevels_surface)
        _surface_axes_labels(
            ax_surface, tracer_var, depth_integrated, clevels_surface, cbar_surface,
            theme)


   In :py:mod:`~nowcast.figures.research.tracer_thalweg_and_surface` we have an extra :py:func:`_calc_clevels` function that calculates contour levels for the two axes and decides whether whether the levels are similar enough that one colour bar is sufficient for the figure,
   or if each axes requires one.

   We have also separated the axes labeling and prettifying code into separate functions,
   :py:func:`_thalweg_axes_labels`,
   and :py:func:`_surface_axes_labels`.

4. Return the :py:class:`matplotlib.figure.Figure` object to the :py:mod:`nowcast.workers.make_plots` worker:

    .. code-block:: python

        return fig


.. _PrepPlotDataFunction:

:py:func:`_prep_plot_data` Function
===================================

The :py:func:`_prep_plot_data` function is responsible for all of the extraction and preparatory processing of the data that will be plotted in the figure's axes objects.
All of the slicing of the plot data from the dataset objects passed into the :ref:`MakeFigureFunction`,
and any calculations that are required should be done in :py:func:`_prep_plot_data` so that the variables it returns are ready to be passed into plotting methods.

.. code-block:: python

    def _prep_plot_data(tracer_var, mesh_mask, depth_integrated):
        hr = 19
        sj, ej = 200, 800
        si, ei = 20, 395

        tracer_hr = tracer_var[hr]
        masked_tracer_hr = np.ma.masked_where(
            mesh_mask['tmask'][0, ...] == 0, tracer_hr)
        surface_hr = masked_tracer_hr[0, sj:ej, si:ei]

        if depth_integrated:
            grid_heights = mesh_mask.variables['e3t_1d'][:][0].reshape(
                tracer_hr.shape[0], 1, 1)
            height_weighted = masked_tracer_hr[:, sj:ej, si:ei] * grid_heights
            surface_hr = height_weighted.sum(axis=0)

        return SimpleNamespace(
            tracer_var=tracer_var,
            tracer_hr=tracer_hr,
            surface_hr=surface_hr,
            surface_j_limits=(sj, ej),
            surface_i_limits=(si, ei),
            thalweg_depth_limits=(0, 450),
            thalweg_length_limits=(0, 632),
        )

:py:func:`_prep_plot_data` should return a :py:obj:`types.SimpleNamespace`
so that the various data objects to be plotted can be easily accessed using dotted notation;
e.g. :py:obj:`plot_data.tracer_hr`.
Please see :ref:`LibraryCodeReturnSimpleNamespacesFromFunctions` for more details.

In figure modules that use the :py:mod:`salishsea_tools.places` module,
:py:func:`_prep_plot_data` is probably the best place to catch undefined place key errors
Please see :ref:`LibraryCodeSalishSeaToolsPlaces` for more details.


.. _PrepFixAxesFunction:

:py:func:`_prep_fig_axes` Function
==================================

The :py:func:`_prep_fig_axes` function accepts arguments named :kbd:`figsize` and :kbd:`theme`.
:kbd:`figsize` provides the size and shape of the figure area.
:kbd:`theme` provides the :py:mod:`nowcast.figures.website_theme` :ref:`WebsiteTheme` module which defines things like the figure and axes background colours.

.. code-block:: python

    def _prep_fig_axes(figsize, theme):
        fig = plt.figure(
            figsize=figsize, facecolor=theme.COLOURS['figure']['facecolor'])

        gs = gridspec.GridSpec(1, 2, width_ratios=[1.618, 1])

        ax_thalweg = fig.add_subplot(gs[0])
        ax_thalweg.set_axis_bgcolor(theme.COLOURS['axes']['background'])

        ax_surface = fig.add_subplot(gs[1])
        ax_surface.set_axis_bgcolor(theme.COLOURS['axes']['background'])

        return fig, (ax_thalweg, ax_surface)

The :py:mod:`nowcast.figures.website_theme` module provides:

* a colour to match the web page background colour that is used as the figure :py:attr:`facecolor`: :py:attr:`theme.COLOURS['figure']['facecolor']`
* a background colour for the axes objects that is set using the :py:meth:`set_axis_bgcolor` method: :py:attr:`theme.COLOURS['axes']['background']`

The function returns

* a :py:obj:`matplotlib.figure.Figure` object
* a tuple of :py:obj:`matplotlib.axes.Axes` objects,
  one for each axes in the figure


Axes Plotting Functions
=======================

After preparing the plot data,
and setting up the figure and axes objects,
our example :ref:`MakeFigureFunction` calls 2 axes plotting functions:

1. :ref:`PlotTracerThalweg`
2. :ref:`PlotTracerSurface`

one for each :py:obj:`matplotlib.axes.Axes` object returned by :py:func:`_prep_fig_axes`.

Those functions generally accept:

* a :py:obj:`matplotlib.axes.Axes` object as their 1st argument,
  called :kbd:`ax` by convention
* the :py:obj:`~types.SimpleNamespace` object that was returned by the :py:func:`_prep_plot_data` function,
  called :kbd:`plot_data` by convention
* the :py:mod:`nowcast.figures.website_theme` module as their last argument,
  called :kbd:`theme` by convention

They may accept other arguments as necessary.

The job of the :py:func:`_plot_*` functions is to act on the :py:obj:`matplotlib.axes.Axes` object
(:kbd:`ax`)
so they may or may not return anything.


.. _PlotTracerThalweg:

:py:func:`_plot_tracer_thalweg` Function
----------------------------------------

The :py:func:`_plot_tracer_thalweg` function in our example plots colour contours of a tracer on a vertical slice along a section of the domain thalweg.

.. code-block:: python

      def _plot_tracer_thalweg(ax, plot_data, bathy, mesh_mask, cmap, clevels):
          cbar = vis.contour_thalweg(
              ax, plot_data.tracer_hr, bathy, mesh_mask, clevels=clevels, cmap=cmap,
              thalweg_file='/SalishSeaCast/tools/bathymetry/thalweg_working.txt',
              cbar_args={'fraction': 0.030, 'pad': 0.04, 'aspect': 45}
          )
          return cbar

This function is a thin wrapper around the :py:func:`salishsea_tools.visualisations.contour_thalweg` function.
It returns the :py:obj:`cbar` colour bar object for a separate :py:func:`_thalweg_axes_labels` function to operate on to handle "making the axes pretty":

.. code-block:: python

    def _thalweg_axes_labels(
        ax, plot_data, show_thalweg_cbar, clevels, cbar, theme
    ):
        ax.set_xlim(plot_data.thalweg_length_limits)
        ax.set_ylim(
            plot_data.thalweg_depth_limits[1], plot_data.thalweg_depth_limits[0])
        if show_thalweg_cbar:
            label = (
                f'{plot_data.tracer_var.long_name} [{plot_data.tracer_var.units}]')
            _cbar_labels(cbar, clevels[::2], theme, label)
        else:
            cbar.remove()
        ax.set_xlabel(
            'Distance along thalweg [km]', color=theme.COLOURS['text']['axis'],
            fontproperties=theme.FONTS['axis'])
        ax.set_ylabel(
            'Depth [m]', color=theme.COLOURS['text']['axis'],
            fontproperties=theme.FONTS['axis'])
        theme.set_axis_colors(ax)

This function shows how text colours and fonts are obtained from :kbd:`theme`.
It finishes with a call to the :py:func:`theme.set_axis_colors` convenience function to set the colours of axis labels,
ticks,
and spines so that they are consistent with the web site theme.

The code format the colour bar labels is in separate :py:func:`_cbar_labels` function so that it can be used by both :py:func:`_thalweg_axes_labels` and :py:func:`_surface_axes_labels`.

.. code-block:: python

    def _cbar_labels(cbar, contour_intervals, theme, label):
        cbar.set_ticks(contour_intervals)
        cbar.ax.axes.tick_params(labelcolor=theme.COLOURS['cbar']['tick labels'])
        cbar.set_label(
            label,
            fontproperties=theme.FONTS['axis'],
            color=theme.COLOURS['text']['axis'])

The colour of the tick labels on the colorbar is set by calling the :py:meth:`axes.tick_params` method on the axes object with a colour provided by :kbd:`theme`.


.. _PlotTracerSurface:

:py:func:`_plot_tracer_surface` Function
----------------------------------------

The :py:func:`_plot_tracer_surface` function is an example of horizontal layer contour plotting on an axes object.

.. code-block:: python

    def _plot_tracer_surface(ax, plot_data, cmap, clevels):
        x, y = np.meshgrid(
            np.arange(*plot_data.surface_i_limits, dtype=int),
            np.arange(*plot_data.surface_j_limits, dtype=int))
        mesh = ax.contourf(
            x, y, plot_data.surface_hr, levels=clevels, cmap=cmap, extend='both')
        cbar = plt.colorbar(mesh, ax=ax, fraction=0.034, pad=0.04, aspect=45)
        return cbar

This function constructs a mesh grid of x-y grid points and uses it and to plot colour contours.
It illustrates how to access the surface tracer field that we returned in the :py:obj:`plot_data` namespace from the :ref:`PrepPlotDataFunction`.

An important consideration when plotting model results as maps for the web site is that the resulting images size must be kept as small as possible so that the page loading time does not become so large that the site is unusable,
especially on slower or mobile networks.
Using the :py:meth:`contourf` method rather than :py:meth:`pcolormesh` is one very effective way of limit the resulting figure image size.
The :py:meth:`contour` method is used to overlay contour lines on the contour map.

The method to add a colorbar to a axes that shows contoured data is not available on the :py:obj:`matplotlib.axes.Axes` object.
Here we use the :py:meth:`colorbar` convenience method provided by :py:obj:`matplotlib.pyplot`
(which we aliases to :py:obj:`plt` on import).

The need to plot colour contours of horizontal data surfaces is general enough that code like this should be refactored into a :py:func:`salishsea_tools.visualisations.contour_layer` function so that :py:func:`_plot_tracer_surface` can become a wrapper like the :ref:`PlotTracerThalweg`.

Similar to the :ref:`PlotTracerThalweg`,
this function returns the :py:obj:`cbar` colour bar object for a separate :py:func:`_surface_axes_labels` function to operate on to handle "making the axes pretty".


.. _AutomaticModuleDocumentationGeneration:

Automatic Module Documentation Generation
=========================================

When you create a new figure module don't forget to add it to the :file:`SalishSeaNowcast/docs/workers.rst` file so that documentation will be generated for it.
For our example,
the content added to :file:`SalishSeaNowcast/docs/workers.rst` is:

.. code-block:: restructuredtext

    .. _nowcast.figures.research.tracer_thalweg_and_surface:

    :py:mod:`nowcast.figures.research.tracer_thalweg_and_surface` Module
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    .. automodule:: nowcast.figures.research.tracer_thalweg_and_surface
        :members:


.. _AutomaticCodeFormatting:

Automatic Code Formatting
=========================

The :kbd:`SalishSeaNowcast` package uses the `yapf`_ code formatting tool to maintain a coding style that is very close to `PEP 8`_.

.. _yapf: https://github.com/google/yapf
.. _PEP 8: https://www.python.org/dev/peps/pep-0008/

:command:`yapf` is installed as part of the :ref:`NowcastFiguresDevEnv` setup.

Before each commit of your figure module please run :program:`yapf` to automatically format your code.
For our example :py:mod:`~nowcast.figures.research.tracer_thalweg_and_surface` module the command would be:

.. code-block:: bash

    $ yapf --in-place nowcast/figures/research/tracer_thalweg_and_surface.py
