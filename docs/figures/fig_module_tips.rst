..  Copyright 2013 – present by the SalishSeaCast Project contributors
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

.. SPDX-License-Identifier: Apache-2.0


.. _FigureModuleTips:

******************
Figure Module Tips
******************

This section contains pointers to useful visualization functions in the :kbd:`SalishSeaTools` package.
It also contains pointers to website figure module functions that do common things so that you can copy code rather than having to reinvent the wheel.


Format Date/Time Tick Labels on an Axes
=======================================

See :py:func:`nowcast.figures.publish.compare_tide_prediction_max_ssh._residual_time_series_labels` for an example of how to use a :py:class:`matplotlib.dates.DateFormatter` object to format date/time tick labels on an axes.


Correct Timezone for Axes Date/Time Tick Labels
===============================================

See :py:func:`nowcast.figures.publish.compare_tide_prediction_max_ssh._residual_time_series_labels` for an example of how to ensure that axes date/time tick labels produced by a :py:class:`matplotlib.dates.DateFormatter` object are correct when the time series data being plotted is timezone-aware..
