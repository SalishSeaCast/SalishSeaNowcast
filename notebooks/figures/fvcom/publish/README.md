The Jupyter Notebooks in this directory are for development and testing of
the results figures generation modules of the SalishSeaCast automation system.

The links below are to static renderings of the notebooks via
[nbviewer.org](https://nbviewer.org/).
Descriptions under the links below are from the first cell of the notebooks
(if that cell contains Markdown or raw text).

* ## [TestTideStnWaterLevel.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/publish/TestTideStnWaterLevel.ipynb)

    **Test `tide_stn_water_level` Module**

    Render figure object produced by the `nowcast.figures.fvcom.tide_stn_water_level` module.
    Provides data for visual testing to confirm that refactoring has not adversely changed figure for web page.

    Set-up and function call replicates as nearly as possible what is done in the `nowcast.workers.make_plots` worker.

* ## [TestSecondNarrowsCurrent.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/publish/TestSecondNarrowsCurrent.ipynb)

    **Test `second_narrows_current` Module**

    Render figure object produced by the `nowcast.figures.fvcom.second_narrows_current` module.
    Provides data for visual testing to confirm that refactoring has not adversely changed figure for web page.

    Set-up and function call replicates as nearly as possible what is done in the `nowcast.workers.make_plots` worker.

* ## [DevelopTideStnWaterLevel.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/publish/DevelopTideStnWaterLevel.ipynb)

    **Develop `tide_stn_water_level` Figure Module**

    Development of functions for `nowcast.figures.fvcom.tide_stn_water_level` web site figure module.

* ## [DevelopSecondNarrowsCurrent.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/publish/DevelopSecondNarrowsCurrent.ipynb)

    **Develop `second_narrows_current` Figure Module**

    Development of functions for `nowcast.figures.fvcom.second_narrows_current` web site figure module.


##License

These notebooks and files are copyright 2013 – present
by the SalishSeaCast Project Contributors
and The University of British Columbia.

They are licensed under the Apache License, Version 2.0.
https://www.apache.org/licenses/LICENSE-2.0
Please see the LICENSE file for details of the license.
