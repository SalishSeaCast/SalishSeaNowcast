The Jupyter Notebooks in this directory are for development and testing of
the results figures generation modules of the SalishSeaCast automation system.

The links below are to static renderings of the notebooks via
[nbviewer.org](https://nbviewer.org/).
Descriptions below the links are from the first cell of the notebooks
(if that cell contains Markdown or raw text).

* ## [TestCompareVENUS_CTD.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/comparison/TestCompareVENUS_CTD.ipynb)

    **Test `compare_venus_ctd` Module**

    Render figure object produced by the `nowcast.figures.publish.compare_venus_ctd` module.
    Provides data for visual testing to confirm that refactoring has not adversely changed figure for web page.

    Set-up and function call replicates as nearly as possible what is done in the `nowcast.workers.make_plots` worker.

* ## [TestSalinityFerryTrackModule.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/comparison/TestSalinityFerryTrackModule.ipynb)

    **Test `salinity_ferry_track` Module**

    Render figure objects produced by the `nowcast.figures.comparison.salinity_ferry_track` module.
    Provides data for visual testing to confirm that refactoring has not adversely changed figure for web page.

    Set-up and function call replicates as nearly as possible what is done in the `nowcast.workers.make_plots` worker.

* ## [TestSandHeadsWinds.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/comparison/TestSandHeadsWinds.ipynb)

    **Test `sandheads_winds` Module**

    Render figure object produced by the `nowcast.figures.comparison.sandheads_winds` module.

    Set-up and function call replicates as nearly as possible what is done in the `nowcast.workers.make_plots` worker
    to help ensure that the module will work in the nowcast production context.


## License

These notebooks and files are copyright by the
[SalishSeaCast Project Contributors](https://github.com/SalishSeaCast/docs/blob/main/CONTRIBUTORS.rst)
and The University of British Columbia.

They are licensed under the Apache License, Version 2.0.
https://www.apache.org/licenses/LICENSE-2.0
Please see the LICENSE file in this repository for details of the license.
