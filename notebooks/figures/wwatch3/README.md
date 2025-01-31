The Jupyter Notebooks in this directory are for development and testing of
the results figures generation modules of the SalishSeaCast automation system.

The links below are to static renderings of the notebooks via
[nbviewer.org](https://nbviewer.org/).
Descriptions below the links are from the first cell of the notebooks
(if that cell contains Markdown or raw text).

* ## [TestWaveHeightPeriod.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/wwatch3/TestWaveHeightPeriod.ipynb)

    **Test `wave_height_period` Figure Module**

    Render figure object produced by the `nowcast.figures.wwatch3.wave_height_period` module.
    Provides data for visual testing to confirm that refactoring has not adversely changed figure for web page.

    Set-up and function call replicates as nearly as possible what is done in the `nowcast.workers.make_plots` worker.

* ## [DevelopWaveHeightPeriod.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/wwatch3/DevelopWaveHeightPeriod.ipynb)

    **Develop `wave_height_period` Figure Module**

    Development of functions for `nowcast.figures.wwatch3.wave_height_period` web site figure module.


## License

These notebooks and files are copyright by the
[SalishSeaCast Project Contributors](https://github.com/SalishSeaCast/docs/blob/main/CONTRIBUTORS.rst)
and The University of British Columbia.

They are licensed under the Apache License, Version 2.0.
https://www.apache.org/licenses/LICENSE-2.0
Please see the LICENSE file in this repository for details of the license.
