.. Copyright 2013-2016 The Salish Sea MEOPAR contributors
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


.. _SalishSeaNowcastSystemWorkers:

*********************************
Salish Sea Nowcast System Workers
*********************************

Process Flow
============

.. figure:: ProcessFlow.svg
    :align: center

    Work flow of preparation for and execution of the daily runs.

The green boxes in the figure above are the workers described below.

The :ref:`Scheduler` is a long-running process that periodically checks the system clock and launches workers when their scheduled time to run is reached.


Workers
=======

:kbd:`download_weather`
-----------------------

.. automodule:: nowcast.workers.download_weather
    :members: main


:kbd:`next_workers` Module
==========================

.. automodule:: nowcast.next_workers
    :members:
