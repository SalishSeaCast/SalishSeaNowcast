The Jupyter Notebooks in this directory are for development and testing of
the results figures generation modules of the Salish Sea model nowcast system.

The links below are to static renderings of the notebooks via
[nbviewer.jupyter.org](https://nbviewer.jupyter.org).
Descriptions under the links below are from the first cell of the notebooks
(if that cell contains Markdown or raw text).

* ##[DevelopTracerThalwegAndSurfaceModule.ipynb](https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/research/DevelopTracerThalwegAndSurfaceModule.ipynb)  
    
    **Develop `tracer_thalweg_and_surface` Figure Module**  
      
    Development of functions for `nowcast.figures.research.tracer_thalweg_and_surface` web site figure module.  
      
    This is an example of developing the functions for a web site figure module in a notebook.  
    It follows the function organization patterns described in  
    [Creating a Figure Module](https://salishsea-nowcast.readthedocs.io/en/latest/figures/create_fig_module.html) docs.  

* ##[TestTracerThalwegAndSurface.ipynb](https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/research/TestTracerThalwegAndSurface.ipynb)  
    
    **Test `tracer_thalweg_and_surface` Module**  
      
    Render figure object produced by the `nowcast.figures.research.tracer_thalweg_and_surface` module.  
      
    Set-up and function call replicates as nearly as possible what is done in the `nowcast.workers.make_plots` worker  
    to help ensure that the module will work in the nowcast production context.  


##License

These notebooks and files are copyright 2013-2017
by the Salish Sea MEOPAR Project Contributors
and The University of British Columbia.

They are licensed under the Apache License, Version 2.0.
https://www.apache.org/licenses/LICENSE-2.0
Please see the LICENSE file for details of the license.
