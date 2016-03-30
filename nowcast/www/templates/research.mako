:orphan: True

.. raw:: html

    <span id="top"></span>

**********************************************************************
Salish Sea Model Research Evaluation Results from ${run_title}
**********************************************************************

*******************************************
${results_date.format('dddd, D MMMM YYYY')}
*******************************************


Disclaimer
----------

This page presents output from a research project.
Results on this page are either 1) not yet evaluated or 2) have been evaluated but do not agree well with observations.  For the latter we are working on model modifications.


Reference
=========

Soontiens, N., Allen, S., Latornell, D., Le Souef, K., Machuca, I., Paquin, J.-P., Lu, Y., Thompson, K., Korabel, V. (2015). Storm surges in the Strait of Georgia simulated with a regional model. Atmosphere-Ocean, in press. https://dx.doi.org/10.1080/07055900.2015.1108899


Plots
-----

<%
  run_dmy = run_date.format('DDMMMYY').lower()
%>

.. raw:: html

    <ul class="simple">
      %for _, plot_title in svg_file_roots:
      <li><a href="#${plot_title.replace(' ', '-').lower()}">${plot_title}</a></li>
      %endfor
      <li><a href="#onc-venus-node-locations">ONC VENUS Node Locations</a></li>
    </ul>

    %for svg_file, plot_title in svg_file_roots:
    <h3 id="${plot_title.replace(' ', '-').lower()}">${plot_title}<a class="headerlink" href="#${plot_title.replace(' ', '-').lower()}" title="Permalink to this headline">¶</a></h3>
    <img class="img-responsive" src="${figures_server}/${run_type}/${run_dmy}/${svg_file}_${run_dmy}.svg" alt="${plot_title} image">
    <p><a href="#top">Back to top</a></p>
    %endfor
    <h3 id="onc-venus-node-locations">ONC VENUS Node Locations<a class="headerlink" href="#onc-venus-node-locations" title="Permalink to this headline">¶</a></h3>
    <object class="img-responsive" type="image/svg+xml" data="../../../../_static/nemo/VENUS_locations.svg"></object>


Data Sources
------------

The forcing data used to drive the Salish Sea model is obtained from several sources:

1. Winds and meteorological conditions

   * `High Resolution Deterministic Prediction System`_ (HRDPS) from Environment Canada.

     .. _High Resolution Deterministic Prediction System: https://weather.gc.ca/grib/grib2_HRDPS_HR_e.html

2. Open boundary conditions

   * `NOAA Storm Surge Forecast`_ at Neah Bay, WA.

     .. _NOAA Storm Surge Forecast: http://www.nws.noaa.gov/mdl/etsurge/index.php?page=stn&region=wc&datum=msl&list=wc&map=0-48&type=both&stn=waneah

3. Rivers

   * Fraser river: Real-time Environment Canada data at `Hope`_
   * Other rivers: J. Morrison , M. G. G. Foreman and D. Masson, 2012. A method for estimating monthly freshwater discharge affecting British Columbia coastal waters, Atmosphere-Ocean, 50:1, 1-8

     .. _Hope: https://wateroffice.ec.gc.ca/report/report_e.html?mode=Table&type=realTime&stn=08MF005&dataType=Real-Time&startDate=2014-12-30&endDate=2015-01-06&prm1=47&prm2=-1

4. Tidal constituents

   * Tidal predictions were generated using constituents from the Canadian Hydrographic Service.

This product has been produced by the **Department of Earth, Ocean and Atmospheric Sciences, University of British Columbia** based on Canadian Hydrographic Charts and/or data, pursuant to CHS Direct User Licence No. 2015-0303-1260-S.

The incorporation of data sourced from CHS in this product shall not be construed as constituting an endorsement by CHS of this product.

This product does not meet the requirements of the *Charts and Nautical Publications Regulations, 1995* under the *Canada Shipping Act, 2001*. Official charts and publications, corrected and up-to-date, must be used to meet the requirements of those regulations.
