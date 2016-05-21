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


****************************
The Nowcast System Framework
****************************

The Salish Sea Nowcast System is a fully automated software system that runs the Salish Sea NEMO model several times each day to produce nowcast and forecast run results.
The runs use the most up-to-date available forcing data and model products:

* atmospheric forcing from the Environment Canada HRDPS
  (High Resolution Deterministic Prediction System) 2.5 km resolution model
* daily average discharge of the Fraser River from the Environment Canada river gauge at Hope
* sea surface height on the western open boundary from the NOAA storm surge forecast model and tide gauge at Neah Bay, WA

Daily nowcast and forecast runs have been produced since mid-October 2014.

* Summary information from the run results is presented on the https://salishsea.eos.ubc.ca/nemo/results/ page.
* The full collection of results files from each run are stored on the :ref:`SalishSeaModelResultsServer`.
* The nowcast results datasets are publicly available on our ERDDAP server at https://salishsea.eos.ubc.ca/erddap/info/

Presently there are 4 runs each day:

* 24h of physics model time for today (:kbd:`nowcast`)
* 24h of green ocean model time for today  (:kbd:`nowcast-green`)
* 30h of physics model time for tomorrow (:kbd:`forecast`)
* 30h of physics model time for the next day (:kbd:`forecast2`)

The :kbd:`nowcast`,
:kbd:`forecast`,
and :kbd:`forecast2` runs use the NEMO-3.4 :kbd:`SalishSea` configuration.

The :kbd:`nowcast-green` runs use the NEMO-3.6 :kbd:`SOG` (aka :kbd:`SMELT`) configuration.
In addition to being a test-bed for the in-development biogeochemical components of the model,
the :kbd:`nowcast-green` runs are a test-bed for improvements to the physics model as we move toward the next iteration of the nowcast system's NEMO model.


Software Architecture
=====================

The :py:obj:`SalishSeaNowcast` package holds the Python modules that power the nowcast system.
The system workflow looks like:

.. image:: ProcessFlow.svg

Each box in the figure above is a :ref:`NowcastSystemWorker`,
a Python process that is launched by the system to do a particular job and terminate when that job is finished.
The workers are defined in Python modules in the :py:obj:`nowcast.workers` namespace.

The workers are
(almost all)
launched and coordinated by the :ref:`NowcastSystemManager`,
:py:mod:`nowcast.nowcast_mgr`.
Unlike the workers that come and go as needed to do their jobs,
the manager is a long-running Python process that is only stopped and restarted when the system configuration needs to be changed.

After the manager launches a worker they communicate with each other using a messaging system based on the `ZeroMQ`_ distributed messaging framework.

.. _ZeroMQ: http://zeromq.org/

Before we get into the details of the :ref:`NowcastMessagingSystem`,
it is important to mention one more piece of the architecture:
the :ref:`NowcastMessageBroker`,
:py:mod:`nowcast.nowcast_broker`.
The message broker is also a long-running Python process that is almost never stopped and restarted.
It buffers and relays messages between the workers and the manager so that both the workers and the manager can start,
stop,
or restart without affecting one another.


.. _NowcastMessagingSystem:

Nowcast Messaging System
========================


.. _NowcastMessageBroker:

Nowcast Message Broker
======================


.. _NowcastSystemManager:

Nowcast System Manager
======================


.. _NowcastSystemWorker:

Nowcast System Worker
=====================
