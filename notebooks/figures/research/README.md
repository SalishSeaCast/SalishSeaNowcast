The Jupyter Notebooks in this directory are for development and testing of
the results figures generation modules of the SalishSeaCast automation system.

The links below are to static renderings of the notebooks via
[nbviewer.org](https://nbviewer.org/).
Descriptions below the links are from the first cell of the notebooks
(if that cell contains Markdown or raw text).

* ## [TestTimeSeriesPlots.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/TestTimeSeriesPlots.ipynb)

    **Test `time_series_plots` Module**

    Render figure object produced by the `nowcast.figures.research.time_series_plots` module.

    Set-up and function call replicates as nearly as possible what is done in the `nowcast.workers.make_plots` worker
    to help ensure that the module will work in the nowcast production context.

* ## [TestBaynesSoundAGRIF.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/TestBaynesSoundAGRIF.ipynb)

    **Test `baynes_sound_agrif` Module**

    Render figure object produced by the `nowcast.figures.research.baynes_sound_agrif` module.

    Set-up and function call replicates as nearly as possible what is done in the `nowcast.workers.make_plots` worker
    to help ensure that the module will work in the nowcast production context.

* ## [DevelopVelocitySectionAndSurfaceModule.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/DevelopVelocitySectionAndSurfaceModule.ipynb)

    **Develop `velocity_section_and_surface` Figure Module**

    Development of functions for `nowcast.figures.research.velocity_section_and_surface` web site figure module.

    This is an example of developing the functions for a web site figure module in a notebook.
    It follows the function organization patterns described in
    [Creating a Figure Module](https://salishsea-nowcast.readthedocs.io/en/latest/figures/create_fig_module.html) docs.

* ## [DevelopBaynesSoundAGRIF.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/DevelopBaynesSoundAGRIF.ipynb)

    **Develop `baynes_sound_agrif` Figure Module**

    Development of functions for `nowcast.figures.research.baynes_sound_agrif` web site figure module.

    **Goal:** A 4 panel figures showing  surface values of
    temperature, salinity, diatoms biomass, and nitrate concentration
    at 12:30 Pacific time.
    Each panel to show all of the Baynes Sound sub-grid as well as
    a fringe of the full domain on the 3 non-land sides.
    Ideally the axes tick labels will be lon/lat with angled grid lines.

* ## [PlacesandMapForTimeSeries.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/PlacesandMapForTimeSeries.ipynb)

    **Sketch out a Map for Timeseries and Find Good Places ****

* ## [DevelopTimeSeriesPlots.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/DevelopTimeSeriesPlots.ipynb)

    **Develop `time_series_plots` Figure Module**

    Development of functions for `nowcast.figures.research.time_series_plots` web site figure module.

* ## [DevelopFrontPlots.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/DevelopFrontPlots.ipynb)

    **Develop `front_plots` Figure Module**

    Development of functions for `nowcast.figures.research.front_plots` web site figure module.

* ## [DevelopTracerThalwegAndSurfaceModule.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/DevelopTracerThalwegAndSurfaceModule.ipynb)

    **Develop `tracer_thalweg_and_surface` Figure Module**

    Development of functions for `nowcast.figures.research.tracer_thalweg_and_surface` web site figure module.

    This is an example of developing the functions for a web site figure module in a notebook.
    It follows the function organization patterns described in
    [Creating a Figure Module](https://salishsea-nowcast.readthedocs.io/en/latest/figures/create_fig_module.html) docs.

* ## [TestPlotVelNEGridded.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/TestPlotVelNEGridded.ipynb)

    **Test `research_VENUS.plot_vel_NE_gridded` Function**

    Render figure object produced by the `nowcast.figures.research_VENUS.plot_vel_NE_gridded` function.

    Set-up and function call replicates as nearly as possible what is done in the `nowcast.workers.make_plots` worker
    to help ensure that the module will work in the nowcast production context.

    **NOTE:** `research_VENUS.plot_vel_NE_gridded` needs to be refactored into a figure module.

* ## [TestTracerThalwegAndSurface.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/TestTracerThalwegAndSurface.ipynb)

    **Test `tracer_thalweg_and_surface` Module**

    Render figure object produced by the `nowcast.figures.research.tracer_thalweg_and_surface` module.

    Set-up and function call replicates as nearly as possible what is done in the `nowcast.workers.make_plots` worker
    to help ensure that the module will work in the nowcast production context.

* ## [TestVelocitySectionAndSurface.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/TestVelocitySectionAndSurface.ipynb)

    **Test `velocity_section_and_surface` Module**

    Render figure object produced by the `nowcast.figures.research.velocity_section_and_surface` module.

    Set-up and function call replicates as nearly as possible what is done in the `nowcast.workers.make_plots` worker
    to help ensure that the module will work in the nowcast production context.

* ## [TestTracerThalwegAndSurfaceHourly.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/TestTracerThalwegAndSurfaceHourly.ipynb)

    **Test `tracer_thalweg_and_surface_hourly` Module**

    Render figure object produced by the `nowcast.figures.research.tracer_thalweg_and_surface_hourly` module.

    Set-up and function call replicates as nearly as possible what is done in the `nowcast.workers.make_plots` worker
    to help ensure that the module will work in the nowcast production context.


## License

These notebooks and files are copyright by the
[SalishSeaCast Project Contributors](https://github.com/SalishSeaCast/docs/blob/main/CONTRIBUTORS.rst)
and The University of British Columbia.

They are licensed under the Apache License, Version 2.0.
https://www.apache.org/licenses/LICENSE-2.0
Please see the LICENSE file in this repository for details of the license.
