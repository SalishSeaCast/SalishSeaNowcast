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


.. _CreatingNowcastFigures:

Creating Nowcast Figures
========================

The web site figures that display the nowcast system run results are calculated by the :py:mod:`nowcast.workers.make_plots` worker using a collection of modules imported from :py:obj:`nowcast.figures`.
:py:obj:`nowcast.figures` is subdivided into 3 namespaces:

* :py:obj:`nowcast.figures.comparison`
* :py:obj:`nowcast.figures.publish`
* :py:obj:`nowcast.figures.research`

Within each of those namespaces the figure producing functions are organized into a module for each figure.
So,
for example,
the :py:mod:`nowcast.figures.publish.compare_tide_prediction_max_ssh` module contains the code to produce a figure shows a map of the Salish Sea with coloured contours
showing the sea surface height when it is at its maximum at a specified tide
gauge station.
The figure also shows 24 hour time series graphs of raw and corrected model water levels compared to the tidal prediction for the gauge location,
and water level residuals (the difference between the corrected model results and the tidal predictions).

The code in the figure modules is just the code that is specific to creating that one figure.
Generic functions that are useful in the creation of multiple figures are collected in the modules of the :ref:`SalishSeaToolsPackage`.
For example,
:py:func:`salishsea_tools.viz_tools.set_aspect` is used to set the aspect ratio of a figure axes object appropriately for the Salish Sea NEMO model grid.


.. _NowcastFigureExample:

An Example
----------

This section discusses the elements of a :py:obj:`nowcast.figures` module.
We'll use :py:mod:`~nowcast.figures.publish.compare_tide_prediction_max_ssh` as the basis of the example.
The example focuses on the structure of the module and the functions it contains,
as well as the interfaces between those and the rest of the :ref:`SalishSeaNowcastPackage`.
In that spirit,
most of the actual implementation code is excluded from what follows.

First we'll show the module structure as a whole,
and then we'll look at each section in detail.

.. code-block:: python
    :linenos:

    # Copyright 2013-2017 The Salish Sea MEOPAR contributors
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

    """Produce a figure that shows a map of the Salish Sea with coloured contours
    showing the sea surface height when it is at its maximum at a specified tide
    gauge station.
    The figure also shows 24 hour time series graphs of:

    * Raw and corrected model water levels compared to the
      tidal prediction for the gauge location

    * Water level residuals
      (the difference between the corrected model results and the tidal predictions)

    The tidal predictions are calculated by :program:`ttide`
    (http://www.eos.ubc.ca/~rich/#T_Tide).
    Those predictions use Canadian Hydrographic Service (CHS) tidal constituents
    and include all tide constituents.
    The corrected model results take into account the errors that result from using
    only 8 tidal constituents in the model calculations.

    The figure is annotated with the calcualted maximum sea surface height at the
    tide gauge location, the time at which it occurs, the ssh residual, and the
    wind speed and direction at that time.
    """
    from collections import namedtuple

    import arrow
    from matplotlib import gridspec
    from matplotlib.dates import DateFormatter
    import matplotlib.pyplot as plt
    from matplotlib.ticker import NullFormatter
    import numpy as np
    import pytz

    from salishsea_tools import (
        places,
        nc_tools,
        viz_tools,
        wind_tools,
    )

    from nowcast.figures import shared
    import nowcast.figures.website_theme


    def compare_tide_prediction_max_ssh(
        place, grid_T_hr, grids_15m, bathy, weather_path, tidal_predictions,
        timezone,
        figsize=(20, 12), theme=nowcast.figures.website_theme,
    ):
        """Plot tidal prediction and models water level timeseries,
        storm surge residual timeseries, sea surface height contours
        on a Salish Sea map, and summary text for the tide gauge station at
        :kbd:`place`.

        :arg str place: Tide gauge station name;
                        must be a key in :py:obj:`salishsea_tools.places.PLACES`.

        :arg grid_T_hr: Hourly averaged tracer results dataset that includes
                        calculated sea surface height.
        :type grid_T_hr: :py:class:`netCDF4.Dataset`

        :arg dict grids_15m: Collection of 15 minute averaged sea surface height
                             datasets at tide gauge locations,
                             keyed by tide gauge station name.

        :arg bathy: Model bathymetry.
        :type bathy: :py:class:`netCDF4.Dataset`

        :arg str weather_path: The directory where the weather forcing files
                               are stored.

        :arg str tidal_predictions: Path to directory of tidal prediction file.

        :arg str timezone: Timezone to use for presentation of dates and times;
                           e.g. :kbd:`Canada/Pacific`.

        :arg 2-tuple figsize: Figure size (width, height) in inches.

        :arg theme: Module-like object that defines the style elements for the
                    figure. See :py:mod:`nowcast.figures.website_theme` for an
                    example.

        :returns: :py:class:`matplotlib.figure.Figure`
        """
        plot_data = _prep_plot_data(
            place, grid_T_hr, grids_15m, bathy, timezone, weather_path,
            tidal_predictions)
        fig, (ax_info, ax_ssh, ax_map, ax_res) = _prep_fig_axes(figsize, theme)
        _plot_info_box(ax_info, place, plot_data, theme)
        _plot_ssh_time_series(ax_ssh, place, plot_data, theme)
        _plot_residual_time_series(ax_res, plot_data, timezone, theme)
        _plot_ssh_map(ax_map, plot_data, place, theme)
        return fig


    def _prep_plot_data(
        place, grid_T_hr, grids_15m, bathy, timezone, weather_path,
        tidal_predictions,
    ):
        ssh_hr = grid_T_hr.variables['sossheig']
        time_ssh_hr = nc_tools.timestamp(
            grid_T_hr, range(grid_T_hr.variables['time_counter'].size))
        try:
            j, i = places.PLACES[place]['NEMO grid ji']
        except KeyError as e:
            raise KeyError(
                'place name or info key not found in '
                'salishsea_tools.places.PLACES: {}'.format(e))
        itime_max_ssh = np.argmax(ssh_hr[:, j, i])
        time_max_ssh_hr = time_ssh_hr[itime_max_ssh]
        ssh_15m_ts = nc_tools.ssh_timeseries_at_point(
            grids_15m[place], 0, 0, datetimes=True)
        ttide = shared.get_tides(place, tidal_predictions)
        ssh_corr = shared.correct_model_ssh(ssh_15m_ts.ssh, ssh_15m_ts.time, ttide)
        max_ssh_15m, time_max_ssh_15m = shared.find_ssh_max(
            place, ssh_15m_ts, ttide)
        tides_15m = shared.interp_to_model_time(
            ssh_15m_ts.time, ttide.pred_all, ttide.time)
        residual = ssh_15m_ts.ssh - tides_15m
        max_ssh_residual = residual[ssh_15m_ts.time == time_max_ssh_15m][0]
        wind_4h_avg = wind_tools.calc_wind_avg_at_point(
            arrow.get(time_max_ssh_15m), weather_path,
            places.PLACES[place]['wind grid ji'], avg_hrs=-4)
        wind_4h_avg = wind_tools.wind_speed_dir(*wind_4h_avg)
        plot_data = namedtuple(
            'PlotData',
            'ssh_max_field, time_max_ssh_hr, ssh_15m_ts, ssh_corr, '
            'max_ssh_15m, time_max_ssh_15m, residual, max_ssh_residual, '
            'wind_4h_avg, '
            'ttide, bathy')
        return plot_data(
            ssh_max_field=ssh_hr[itime_max_ssh],
            time_max_ssh_hr=time_max_ssh_hr.to(timezone),
            ssh_15m_ts=ssh_15m_ts,
            ssh_corr=ssh_corr,
            max_ssh_15m=max_ssh_15m - places.PLACES[place]['mean sea lvl'],
            time_max_ssh_15m=arrow.get(time_max_ssh_15m).to(timezone),
            residual=residual,
            max_ssh_residual=max_ssh_residual,
            wind_4h_avg=wind_4h_avg,
            ttide=ttide,
            bathy=bathy,
        )


    def _prep_fig_axes(figsize, theme):
        fig = plt.figure(
            figsize=figsize, facecolor=theme.COLOURS['figure']['facecolor'])
        gs = gridspec.GridSpec(3, 2, width_ratios=[2, 1])
        gs.update(wspace=0.13, hspace=0.2)
        ax_info = fig.add_subplot(gs[0, 0])
        ax_ssh = fig.add_subplot(gs[1, 0])
        ax_ssh.set_axis_bgcolor(theme.COLOURS['axes']['background'])
        ax_res = fig.add_subplot(gs[2, 0])
        ax_res.set_axis_bgcolor(theme.COLOURS['axes']['background'])
        ax_map = fig.add_subplot(gs[:, 1])
        fig.autofmt_xdate()
        return fig, (ax_info, ax_ssh, ax_map, ax_res)


      def _plot_info_box(ax, place, plot_data, theme):

          ...

          ax.text(
              0.05, 0.6,
              'Time of max: {datetime} {tzone}'
              .format(
                  datetime=time_max_ssh_15m.format('YYYY-MM-DD HH:mm'),
                  tzone=time_max_ssh_15m.datetime.tzname()),
              horizontalalignment='left', verticalalignment='top',
              transform=ax.transAxes,
              fontproperties=theme.FONTS['info box content'],
              color=theme.COLOURS['text']['info box content'])

          ...

          _info_box_hide_frame(ax, theme)


    def _info_box_hide_frame(ax, theme):
        ax.set_axis_bgcolor(theme.COLOURS['figure']['facecolor'])
        ax.xaxis.set_visible(False)
        ax.yaxis.set_visible(False)
        for spine in ax.spines:
            ax.spines[spine].set_visible(False)


    def _plot_ssh_time_series(ax, place, plot_data, theme, ylims=(-3, 3)):

        ...

        ax.plot(
            plot_data.ttide.time, plot_data.ttide.pred_all,
            linewidth=2, label='Tide Prediction',
            color=theme.COLOURS['time series']['tidal prediction vs model'])

        ...
        ax.legend(numpoints=1)

        _ssh_time_series_labels(ax, place, ylims, theme)


    def _ssh_time_series_labels(ax, place, ylims, theme):
        ax.set_title(
            'Sea Surface Height at {place}'.format(place=place),
            fontproperties=theme.FONTS['axes title'],
            color=theme.COLOURS['text']['axes title'])
        ax.set_ylabel(
            'Water Level wrt MSL [m]',
            fontproperties=theme.FONTS['axis'],
            color=theme.COLOURS['text']['axis'])
        ax.set_ylim(ylims)
        ax.grid(axis='both')
        theme.set_axis_colors(ax)


    def _plot_residual_time_series(
        ax, plot_data, timezone, theme,
        ylims=(-1, 1), yticks=np.arange(-1, 1.25, 0.25),
    ):

        ...

        ax.legend()
        _residual_time_series_labels(
            ax, ylims, yticks, timezone, time[0].tzname(), theme)


    def _residual_time_series_labels(ax, ylims, yticks, timezone, tzname, theme):
        ...
        ax.xaxis.set_major_formatter(
            DateFormatter('%d-%b %H:%M', tz=pytz.timezone(timezone)))
        ...


    def _plot_ssh_map(ax, plot_data, place, theme):
        contour_intervals = [
            -1, -0.5, 0.5, 1, 1.5, 1.6, 1.7, 1.8, 1.9, 2, 2.1, 2.2, 2.4, 2.6]
        mesh = ax.contourf(
            plot_data.ssh_max_field, contour_intervals,
            cmap='nipy_spectral', extend='both', alpha=0.6)
        ax.contour(
            plot_data.ssh_max_field, contour_intervals,
            colors='black', linestyles='--')
        cbar = plt.colorbar(mesh, ax=ax)
        viz_tools.plot_coastline(ax, plot_data.bathy)
        viz_tools.plot_land_mask(ax, plot_data.bathy, color=theme.COLOURS['land'])
        _ssh_map_axis_labels(ax, place, plot_data, theme)
        _ssh_map_cbar_labels(cbar, contour_intervals, theme)


    def _ssh_map_axis_labels(ax, place, plot_data, theme):
        ...


    def _ssh_map_cbar_labels(cbar, contour_intervals, theme):
        cbar.set_ticks(contour_intervals)
        cbar.ax.axes.tick_params(labelcolor=theme.COLOURS['cbar']['tick labels'])
        cbar.set_label(
            'Sea Surface Height [m]',
            fontproperties=theme.FONTS['axis'],
            color=theme.COLOURS['text']['axis'])


Copyright Notice
^^^^^^^^^^^^^^^^

Lines 1-14 are our :ref:`LibraryCodeStandardCopyrightHeaderBlock`:

.. code-block:: python
    :linenos:
    :lineno-start: 1

    # Copyright 2013-2017 The Salish Sea MEOPAR contributors
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

Lines 16-37 are the module docstring.
It will appear at top of the :ref:`LibraryCodeAutoGeneratedDocs`
(:py:mod:`nowcast.figures.publish.compare_tide_prediction_max_ssh` in this case).

.. code-block:: python
    :linenos:
    :lineno-start: 16

    """Produce a figure that shows a map of the Salish Sea with coloured contours
    showing the sea surface height when it is at its maximum at a specified tide
    gauge station.
    The figure also shows 24 hour time series graphs of:

    * Raw and corrected model water levels compared to the
      tidal prediction for the gauge location

    * Water level residuals
      (the difference between the corrected model results and the tidal predictions)

    The tidal predictions are calculated by :program:`ttide`
    (http://www.eos.ubc.ca/~rich/#T_Tide).
    Those predictions use Canadian Hydrographic Service (CHS) tidal constituents
    and include all tide constituents.
    The corrected model results take into account the errors that result from using
    only 8 tidal constituents in the model calculations.

    The figure is annotated with the calcualted maximum sea surface height at the
    tide gauge location, the time at which it occurs, the ssh residual, and the
    wind speed and direction at that time.
    """


Imports
^^^^^^^

Next come the imports
(lines 38-56 in our example):

.. code-block:: python
    :linenos:
    :lineno-start: 38

    from collections import namedtuple

    import arrow
    from matplotlib import gridspec
    from matplotlib.dates import DateFormatter
    import matplotlib.pyplot as plt
    from matplotlib.ticker import NullFormatter
    import numpy as np
    import pytz

    from salishsea_tools import (
        places,
        nc_tools,
        viz_tools,
        wind_tools,
    )

    from nowcast.figures import shared
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


.. _FigureCreationFunction:

Figure Creation Function
^^^^^^^^^^^^^^^^^^^^^^^^

The first function in the module is the function that will be called by the :py:mod:`nowcast.workers.make_plots` worker to return a :py:class:`matplotlib.figure.Figure` object.
This function has the same name as the module.
It is also the module's only :ref:`public function <LibraryCodePublicAndPrivate>` function.

.. code-block:: python
    :linenos:
    :lineno-start: 59

    def compare_tide_prediction_max_ssh(
        place, grid_T_hr, grids_15m, bathy, weather_path, tidal_predictions,
        timezone,
        figsize=(20, 12), theme=nowcast.figures.website_theme,
    ):
        """Plot tidal prediction and models water level timeseries,
        storm surge residual timeseries, sea surface height contours
        on a Salish Sea map, and summary text for the tide gauge station at
        :kbd:`place`.

        :arg str place: Tide gauge station name;
                        must be a key in :py:obj:`salishsea_tools.places.PLACES`.

        :arg grid_T_hr: Hourly averaged tracer results dataset that includes
                        calculated sea surface height.
        :type grid_T_hr: :py:class:`netCDF4.Dataset`

        :arg dict grids_15m: Collection of 15 minute averaged sea surface height
                             datasets at tide gauge locations,
                             keyed by tide gauge station name.

        :arg bathy: Model bathymetry.
        :type bathy: :py:class:`netCDF4.Dataset`

        :arg str weather_path: The directory where the weather forcing files
                               are stored.

        :arg str tidal_predictions: Path to directory of tidal prediction file.

        :arg str timezone: Timezone to use for presentation of dates and times;
                           e.g. :kbd:`Canada/Pacific`.

        :arg 2-tuple figsize: Figure size (width, height) in inches.

        :arg theme: Module-like object that defines the style elements for the
                    figure. See :py:mod:`nowcast.figures.website_theme` for an
                    example.

        :returns: :py:class:`matplotlib.figure.Figure`
        """
        plot_data = _prep_plot_data(
            place, grid_T_hr, grids_15m, bathy, timezone, weather_path,
            tidal_predictions)
        fig, (ax_info, ax_ssh, ax_map, ax_res) = _prep_fig_axes(figsize, theme)
        _plot_info_box(ax_info, place, plot_data, theme)
        _plot_ssh_time_series(ax_ssh, place, plot_data, theme)
        _plot_residual_time_series(ax_res, plot_data, timezone, theme)
        _plot_ssh_map(ax_map, plot_data, place, theme)
        return fig


Function Signature
""""""""""""""""""

The function signature
(lines 59-63)
should use model results dataset objects rather than file names so that the datasets are loaded once by the :py:mod:`nowcast.workers.make_plots` worker and references to them passed into the figure creation functions.

The signature ends with the default-values keyword arguments :kbd:`figsize` and :kbd:`theme`.

The :kbd:`figsize` 2-tuple give the width and height of the figure,
but more importanly its aspect ratio.
Choose values that are appropriate to the information presented in the figure.

The :kbd:`theme` should be defaulted to :py:mod:`nowcast.figures.wehsite_theme`, a module that provides colours and font specifications that fit with the `salishsea site`_ colour scheme and provide consistency among the figures.

.. _salishsea site: https://salishsea.eos.ubc.ca


Function Docstring
""""""""""""""""""

The function docstring
(lines 64-98)
includes description and type information for each of the function arguments.
Those are written using `Sphinx Info Field List markup`_ so that they render nicely in the :ref:`automatically generated module documentation <AutomaticModuleDocumentationGeneration>`.

.. _Sphinx Info Field List markup: http://www.sphinx-doc.org/en/stable/domains.html#info-field-lists

Simple,
1-word type information can be included in the :kbd:`:arg ...:` role,
for example:

.. code-block:: restructuredtext

    :arg str place: Tide gauge station name;
                    must be a key in :py:obj:`salishsea_tools.places.PLACES`.

More complicated type information should go in a separate :kbd:`:type ...:` role like:

.. code-block:: restructuredtext

    :arg grid_T_hr: Hourly averaged tracer results dataset that includes
                    calculated sea surface height.
    :type grid_T_hr: :py:class:`netCDF4.Dataset`


Function Code
"""""""""""""

The function code does 4 things:

1. Call a module-private function :py:func:`_prep_plot_data` to prepare the collection of objects that contain the data that will be plotted in the figure
   (lines 99-101).

2. Call a module-private function :py:func:`_prep_fig_axes`
   (line 102).
   That function returns:

   * a :py:obj:`matplotlib.figure.Figure` object
   * a tuple of :py:obj:`matplotlib.axes.Axes` objects,
     one for each axes in the figure

   The :py:func:`_prep_fig_axes` function accept arguments named :kbd:`figsize` and :kbd:`theme`.
   :kbd:`figsize` provides the size and shape of the figure area.
   :kbd:`theme` provides the :py:mod:`nowcast.figures.website_theme` :ref:`WebsiteTheme` module which defines things like the figure and axes background colours.

   The tuple of axes objects returned by :py:func:`_prep_fig_axes` should be given meaningful names;
   i.e.

   .. code-block:: python
        :linenos:
        :lineno-start: 102

        fig, (ax_info, ax_ssh, ax_map, ax_res) = _prep_fig_axes(figsize, theme)

   rather than:

   .. code-block:: python

        fig, (ax1, ax2, ax2, ax4) = _prep_fig_axes(figsize, theme)

3. For each axes object returned by :py:func:`_prep_fig_axes`,
   call a module-private function whose name starts with :py:func:`_plot_` to draw all the things on the axes
   (lines 103-106).

4. Return the :py:obj:`matplotlib.figure.Figure` object to the :py:mod:`nowcast.workers.make_plots` worker
   (line 107).


:py:func:`_prep_plot_data` Function
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :py:func:`_prep_plot_data` function is responsible for all of the extraction and preparatory processing of the data that will be plotted in the figure's axes objects.
All of the slicing of the plot data from the dataset objects passed into the :ref:`FigureCreationFunction`,
and any calculations that are required should be done in :py:func:`_prep_plot_data` so that the variables it returns are ready to be passed into plotting methods.

.. code-block:: python
    :linenos:
    :lineno-start: 110

    def _prep_plot_data(
        place, grid_T_hr, grids_15m, bathy, timezone, weather_path,
        tidal_predictions,
    ):
        ssh_hr = grid_T_hr.variables['sossheig']
        time_ssh_hr = nc_tools.timestamp(
            grid_T_hr, range(grid_T_hr.variables['time_counter'].size))
        try:
            j, i = places.PLACES[place]['NEMO grid ji']
        except KeyError as e:
            raise KeyError(
                'place name or info key not found in '
                'salishsea_tools.places.PLACES: {}'.format(e))
        itime_max_ssh = np.argmax(ssh_hr[:, j, i])
        time_max_ssh_hr = time_ssh_hr[itime_max_ssh]
        ssh_15m_ts = nc_tools.ssh_timeseries_at_point(
            grids_15m[place], 0, 0, datetimes=True)
        ttide = shared.get_tides(place, tidal_predictions)
        ssh_corr = shared.correct_model_ssh(ssh_15m_ts.ssh, ssh_15m_ts.time, ttide)
        max_ssh_15m, time_max_ssh_15m = shared.find_ssh_max(
            place, ssh_15m_ts, ttide)
        tides_15m = shared.interp_to_model_time(
            ssh_15m_ts.time, ttide.pred_all, ttide.time)
        residual = ssh_15m_ts.ssh - tides_15m
        max_ssh_residual = residual[ssh_15m_ts.time == time_max_ssh_15m][0]
        wind_4h_avg = wind_tools.calc_wind_avg_at_point(
            arrow.get(time_max_ssh_15m), weather_path,
            places.PLACES[place]['wind grid ji'], avg_hrs=-4)
        wind_4h_avg = wind_tools.wind_speed_dir(*wind_4h_avg)
        plot_data = namedtuple(
            'PlotData',
            'ssh_max_field, time_max_ssh_hr, ssh_15m_ts, ssh_corr, '
            'max_ssh_15m, time_max_ssh_15m, residual, max_ssh_residual, '
            'wind_4h_avg, '
            'ttide, bathy')
        return plot_data(
            ssh_max_field=ssh_hr[itime_max_ssh],
            time_max_ssh_hr=time_max_ssh_hr.to(timezone),
            ssh_15m_ts=ssh_15m_ts,
            ssh_corr=ssh_corr,
            max_ssh_15m=max_ssh_15m - places.PLACES[place]['mean sea lvl'],
            time_max_ssh_15m=arrow.get(time_max_ssh_15m).to(timezone),
            residual=residual,
            max_ssh_residual=max_ssh_residual,
            wind_4h_avg=wind_4h_avg,
            ttide=ttide,
            bathy=bathy,
        )

:py:func:`_prep_plot_data` should return a :py:obj:`namedtuple`
(lines 140-157)
so that the various data objects to be plotted can be easily accessed using dotted notation;
e.g. :py:obj:`plot_data.max_ssh_15m`.
Please see :ref:`LibraryCodeReturnNamedtuplesFromFunctions` for more details.

In figure modules that use the :py:mod:`salishsea_tools.places` module,
:py:func:`_prep_plot_data` is probably the best place to catch undefined place key errors
(lines 117-122).
Please see :ref:`LibraryCodeSalishSeaToolsPlaces` for more details.


:py:func:`_prep_fig_axes` Function
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :py:func:`_prep_fig_axes` function accept arguments named :kbd:`figsize` and :kbd:`theme`.
:kbd:`figsize` provides the size and shape of the figure area.
:kbd:`theme` provides the :py:mod:`nowcast.figures.website_theme` :ref:`WebsiteTheme` module which defines things like the figure and axes background colours.

.. code-block:: python
    :linenos:
    :lineno-start: 160

    def _prep_fig_axes(figsize, theme):
        fig = plt.figure(
            figsize=figsize, facecolor=theme.COLOURS['figure']['facecolor'])
        gs = gridspec.GridSpec(3, 2, width_ratios=[2, 1])
        gs.update(wspace=0.13, hspace=0.2)
        ax_info = fig.add_subplot(gs[0, 0])
        ax_ssh = fig.add_subplot(gs[1, 0])
        ax_ssh.set_axis_bgcolor(theme.COLOURS['axes']['background'])
        ax_res = fig.add_subplot(gs[2, 0])
        ax_res.set_axis_bgcolor(theme.COLOURS['axes']['background'])
        ax_map = fig.add_subplot(gs[:, 1])
        fig.autofmt_xdate()
        return fig, (ax_info, ax_ssh, ax_map, ax_res)

The :py:mod:`nowcast.figures.website_theme` module provides:

* a colour to match the web page background colour that is used as the figure :py:attr:`facecolor` (line 162): :py:attr:`theme.COLOURS['figure']['facecolor']`
* a background colour for the axes objects that is set using the :py:meth:`set_axis_bgcolor` method (lines 167 and 169): :py:attr:`theme.COLOURS['axes']['background']`

The function returns
(line 172):

* a :py:obj:`matplotlib.figure.Figure` object
* a tuple of :py:obj:`matplotlib.axes.Axes` objects,
  one for each axes in the figure


Axes Plotting Functions
^^^^^^^^^^^^^^^^^^^^^^^

After preparing the plot data,
and setting up the figure and axes objects,
our example :ref:`FigureCreationFunction` calls 4 axes plotting functions:

1. :ref:`PlotInfoBoxFunction`
2. :ref:`PlotSshTimeSeriesFunction`
3. :ref:`PlotResidualTimeSeriesFunction`
4. :ref:`PlotSshMapFunction`

one for each :py:obj:`matplotlib.axes.Axes` object returned by :py:func:`_prep_fig_axes`.

Those functions generally accept:

* a :py:obj:`matplotlib.axes.Axes` object as their 1st argument,
  called :kbd:`ax` by convention
* the :py:obj:`namedtuple` object that was returned by the :py:func:`_prep_plot_data` function,
  called :kbd:`plot_data` by convention
* the :py:mod:`nowcast.figures.website_theme` module as their last argument,
  called :kbd:`theme` by convention

They may accept other arguments as necessary.

The job of the :py:func:`_plot_*` functions is to act on the :py:obj:`matplotlib.axes.Axes` object
(:kbd:`ax`)
so they do not return anything.


.. _PlotInfoBoxFunction:

:py:func:`_plot_info_box` Function
""""""""""""""""""""""""""""""""""

The :py:func:`_plot_info_box` function in our example plots text on the figure using an axes object whose spines,
labels,
etc.
are hidden.

.. code-block:: python
    :linenos:
    :lineno-start: 175

      def _plot_info_box(ax, place, plot_data, theme):

          ...

          ax.text(
              0.05, 0.6,
              'Time of max: {datetime} {tzone}'
              .format(
                  datetime=time_max_ssh_15m.format('YYYY-MM-DD HH:mm'),
                  tzone=time_max_ssh_15m.datetime.tzname()),
              horizontalalignment='left', verticalalignment='top',
              transform=ax.transAxes,
              fontproperties=theme.FONTS['info box content'],
              color=theme.COLOURS['text']['info box content'])

          ...

          _info_box_hide_frame(ax, theme)

The abbreviated version above shows how text is placed and aligned,
and how font properties and the text colour are set from :kbd:`theme`.

Also shown is how an `arrow`_ datetime object is formatted for display,
and how its abbreviated timezone name
(e.g. :kbd:`PDT`)
is obtained.

.. _arrow: http://crsmithdev.com/arrow/

A separate function,
:py:func:`_info_box_hide_frame`,
is called to hide most of the axes elements and set its background colour so that the text appears to be plotted on the figure canvas:

.. code-block:: python
    :linenos:
    :lineno-start: 195

    def _info_box_hide_frame(ax, theme):
        ax.set_axis_bgcolor(theme.COLOURS['figure']['facecolor'])
        ax.xaxis.set_visible(False)
        ax.yaxis.set_visible(False)
        for spine in ax.spines:
            ax.spines[spine].set_visible(False)


.. _PlotSshTimeSeriesFunction:

:py:func:`_plot_ssh_time_series` Function
"""""""""""""""""""""""""""""""""""""""""

The :py:func:`_plot_ssh_time_series` function is an example of a line plotting function with a legend on the axes.

.. code-block:: python
    :linenos:
    :lineno-start: 203

    def _plot_ssh_time_series(ax, place, plot_data, theme, ylims=(-3, 3)):

        ...

        ax.plot(
            plot_data.ttide.time, plot_data.ttide.pred_all,
            linewidth=2, label='Tide Prediction',
            color=theme.COLOURS['time series']['tidal prediction vs model'])

        ...
        ax.legend(numpoints=1)

        _ssh_time_series_labels(ax, place, ylims, theme)

The abbreviated version above shows how elements from the :kbd:`plot_data` object are access,
how the line width,
and legend label are set,
and how the line colour is obtained from :kbd:`theme`.
The axes object :py:meth:`legend` method is called to render the labels assigned in the :py:meth:`plot` method calls with the corresponding line and marker samples.

A separate function,
:py:func:`_ssh_time_series_labels`,
is called to handle "making the axes pretty":

.. code-block:: python
    :linenos:
    :lineno-start: 218

    def _ssh_time_series_labels(ax, place, ylims, theme):
        ax.set_title(
            'Sea Surface Height at {place}'.format(place=place),
            fontproperties=theme.FONTS['axes title'],
            color=theme.COLOURS['text']['axes title'])
        ax.set_ylabel(
            'Water Level wrt MSL [m]',
            fontproperties=theme.FONTS['axis'],
            color=theme.COLOURS['text']['axis'])
        ax.set_ylim(ylims)
        ax.grid(axis='both')
        theme.set_axis_colors(ax)

Apart from more text plotting with the :py:meth:`set_title` and :py:meth:`set_ylabel` methods,
this function also handles setting axis limits,
and grid visibility.
Finally,
it calls the :py:func:`theme.set_axis_colors` convenience function to set the colours of axis labels,
ticks,
and spines so that they are consistent with the web site theme.


.. _PlotResidualTimeSeriesFunction:

:py:func:`_plot_residual_time_series` Function
""""""""""""""""""""""""""""""""""""""""""""""

The :py:func:`_plot_residual_time_series` function is conceptually similar to the :ref:`PlotSshTimeSeriesFunction`.
It just operates on a different axes object.

.. code-block:: python
    :linenos:
    :lineno-start: 232

    def _plot_residual_time_series(
        ax, plot_data, timezone, theme,
        ylims=(-1, 1), yticks=np.arange(-1, 1.25, 0.25),
    ):

        ...

        ax.legend()
        _residual_time_series_labels(
            ax, ylims, yticks, timezone, time[0].tzname(), theme)

It too has its own "make it pretty" function:

.. code-block:: python
    :linenos:
    :lineno-start: 244

    def _residual_time_series_labels(ax, ylims, yticks, timezone, tzname, theme):
        ...
        ax.xaxis.set_major_formatter(
            DateFormatter('%d-%b %H:%M', tz=pytz.timezone(timezone)))
        ...

Here we see how to use a :py:class:`matplotlib.dates.DateFormatter` object to format date/time tick labels on an axes,
and how to ensure that those label are correct when the time series data being plotted is timezone-aware.


.. _PlotSshMapFunction:

:py:func:`_plot_ssh_map` Function
"""""""""""""""""""""""""""""""""

The :py:func:`_plot_ssh_map` function is an example of a plotting function that displays a contour map of a field variable,
contour lines,
and land regions of the model domain:

.. code-block:: python
    :linenos:
    :lineno-start: 251

    def _plot_ssh_map(ax, plot_data, place, theme):
        contour_intervals = [
            -1, -0.5, 0.5, 1, 1.5, 1.6, 1.7, 1.8, 1.9, 2, 2.1, 2.2, 2.4, 2.6]
        mesh = ax.contourf(
            plot_data.ssh_max_field, contour_intervals,
            cmap='nipy_spectral', extend='both', alpha=0.6)
        ax.contour(
            plot_data.ssh_max_field, contour_intervals,
            colors='black', linestyles='--')
        cbar = plt.colorbar(mesh, ax=ax)
        viz_tools.plot_coastline(ax, plot_data.bathy)
        viz_tools.plot_land_mask(
            ax, plot_data.bathy, color=theme.COLOURS['land'])
        _ssh_map_axis_labels(ax, place, plot_data, theme)
        _ssh_map_cbar_labels(cbar, contour_intervals, theme)

An important consideration when plotting model results as maps for the web site is that the resulting images size must be kept as small as possible so that the page loading time does not become so large that the site is unusable,
especially on slower or mobile networks.
Using the :py:meth:`contourf` method rather than :py:meth:`pcolormesh` is one very effective way of limit the resulting figure image size.
The :py:meth:`contour` method is used to overlay contour lines on the contour map.

The method to add a colorbar to a axes that shows contoured data is not available on the :py:obj:`matplotlib.axes.Axes` object.
Here we use the :py:meth:`colorbar` convenience method provided by :py:obj:`matplotlib.pyplot`
(which we aliases to :py:obj:`plt` on import).

The :py:func:`salishsea_tools.viz_tools.plot_coastline` and :py:func:`salishsea_tools.viz_tools.plot_land_mask` functions provide space-efficient ways of adding the coastline and land regions to the axes.

Finally we have a function,
:py:func:`_ssh_map_axis_labels`,
to label the contour map part of the axes,
and the :py:func:`_ssh_map_cbar_labels` to label the colorbar part:

.. code-block:: python
    :linenos:
    :lineno-start: 267

    def _ssh_map_axis_labels(ax, place, plot_data, theme):
        ...


    def _ssh_map_cbar_labels(cbar, contour_intervals, theme):
        cbar.set_ticks(contour_intervals)
        cbar.ax.axes.tick_params(labelcolor=theme.COLOURS['cbar']['tick labels'])
        cbar.set_label(
            'Sea Surface Height [m]',
            fontproperties=theme.FONTS['axis'],
            color=theme.COLOURS['text']['axis'])

The colour of the tick labels on the colorbar is set by calling the :py:meth:`axes.tick_params` method on the axes object with a colour provided by :kbd:`theme`.


.. _AutomaticModuleDocumentationGeneration:

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
