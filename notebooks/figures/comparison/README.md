The Jupyter Notebooks in this directory are for development and testing of
the results figures generation modules of the Salish Sea model nowcast system.

The links below are to static renderings of the notebooks via
[nbviewer.jupyter.org](http://nbviewer.jupyter.org/).
Descriptions under the links below are from the first cell of the notebooks
(if that cell contains Markdown or raw text).

* ##[TestCompareVENUS_CTD.ipynb](http://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/comparison/TestCompareVENUS_CTD.ipynb)  
    
    **Test `compare_venus_ctd` Module**  
      
    Render figure object produced by the `nowcast.figures.publish.compare_venus_ctd` module.  
    Provides data for visual testing to confirm that refactoring has not adversely changed figure for web page.  
      
    Set-up and function call replicates as nearly as possible what is done in the `nowcast.workers.make_plots` worker.  

* ##[TestSalinityFerryTrackModule.ipynb](http://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/comparison/TestSalinityFerryTrackModule.ipynb)  
    
    **Test `salinity_ferry_track` Module**  
      
    Render figure objects produced by the `nowcast.figures.comparison.salinity_ferry_track` module.  
    Provides data for visual testing to confirm that refactoring has not adversely changed figure for web page.  
      
    Set-up and function call replicates as nearly as possible what is done in the `nowcast.workers.make_plots` worker.  


##License

These notebooks and files are copyright 2013-2017
by the Salish Sea MEOPAR Project Contributors
and The University of British Columbia.

They are licensed under the Apache License, Version 2.0.
http://www.apache.org/licenses/LICENSE-2.0
Please see the LICENSE file for details of the license.
