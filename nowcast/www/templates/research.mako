:orphan: True

**********************************************************************
Salish Sea Model Research Evaluation Results from ${run_title}
**********************************************************************

****************************************
${results_date.strftime('%A, %d %B %Y')}
****************************************


Disclaimer
==========

This page presents output from a research project.
Results on this page are either 1) not yet evaluated or 2) have been evaluated but do not agree well with observations.  For the latter we are working on model modifications.


Reference
---------

Soontiens, N., Allen, S., Latornell, D., Le Souef, K., Machuca, I., Paquin, J.-P., Lu, Y., Thompson, K., Korabel, V. (2015). Storm surges in the Strait of Georgia simulated with a regional model. Submitted to Atmosphere-Ocean.


Plots
=====

.. raw:: html
    <%
        run_dmy = run_date.strftime('%d%b%y').lower()
    %>
    %for svg_file in svg_file_roots:
    <object class="img-responsive" type="image/svg+xml"
      data="../../../../_static/nemo/results_figures/${run_type}/${run_dmy}/${svg_file}_${run_dmy}.svg">
    </object>
    <hr>
    %endfor
    <object class="img-responsive" type="image/svg+xml"
      data="../../../../_static/nemo/VENUS_locations.svg">
    </object>  
    <hr>

Data Sources
============

The forcing data used to drive the Salish Sea model is obtained from several sources:

1. Winds and meteorological conditions

   * `High Resolution Deterministic Prediction System`_ (HRDPS) from Environment Canada.

2. Open boundary conditions

   * `NOAA Storm Surge Forecast`_ at Neah Bay, WA.

3. Rivers

   * Fraser river: Real-time Environment Canada data at `Hope`_
   * Other rivers: J. Morrison , M. G. G. Foreman and D. Masson, 2012. A method for estimating monthly freshwater discharge affecting British Columbia coastal waters, Atmosphere-Ocean, 50:1, 1-8

4. Tidal constituents

   * Tidal predictions were generated using constituents from the Canadian Hydrographic Service.


.. _High Resolution Deterministic Prediction System: https://weather.gc.ca/grib/grib2_HRDPS_HR_e.html
.. _NOAA Storm Surge Forecast: http://www.nws.noaa.gov/mdl/etsurge/index.php?page=stn&region=wc&datum=msl&list=wc&map=0-48&type=both&stn=waneah
.. _Hope: https://wateroffice.ec.gc.ca/report/report_e.html?mode=Table&type=realTime&stn=08MF005&dataType=Real-Time&startDate=2014-12-30&endDate=2015-01-06&prm1=47&prm2=-1

This product has been produced by the **Department of Earth, Ocean and Atmospheric Sciences, University of British Columbia** based on Canadian Hydrographic Charts and/or data, pursuant to CHS Direct User Licence No. 2015-0303-1260-S.

The incorporation of data sourced from CHS in this product shall not be construed as constituting an endorsement by CHS of this product.

This product does not meet the requirements of the *Charts and Nautical Publications Regulations, 1995* under the *Canada Shipping Act, 2001*. Official charts and publications, corrected and up-to-date, must be used to meet the requirements of those regulations.
