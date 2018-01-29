.. Copyright 2013-2018 The Salish Sea MEOPAR contributors
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


.. _NowcastProductionDeployment:

*****************************
Nowcast Production Deployment
*****************************

In October 2016 the production deployment of the nowcast system was changed to use the :ref:`SalishSeaNowcast-repo` package that is based on the `NEMO_Nowcast framework`_ framework.
The production deployment uses 3 systems:

.. _NEMO_Nowcast framework: http://nemo-nowcast.readthedocs.io/en/latest/

#. The :py:mod:`nemo_nowcast.message_broker`,
   :py:mod:`nemo_nowcast.manager`,
   :py:mod:`nemo_nowcast.scheduler`,
   :py:mod:`nemo_nowcast.log_aggregator`,
   most of the pre- and post-processing workers run on the :ref:`SalishSeaModelResultsServer`, :kbd:`skookum`, where the deployment is in the :file:`/results/nowcast-sys/` directory tree.

#. The development compute server,
   :kbd:`salish`,
   is used to run the daily development model run,
   :kbd:`nowcast-dev` NEMO-3.6 model run,
   and the :py:mod:`nowcast.workers.make_live_ocean_files` worker that relies on Matlab.
   :kbd:`salish` and :kbd:`skookum` share storage via NFS mounts,
   so,
   :kbd:`salish` uses the same deployment is in the :file:`/results/nowcast-sys/` directory tree.

#. The daily
   :kbd:`forecast2`
   (preliminary forecast),
   :kbd:`nowcast`,
   :kbd:`forecast`,
   and :kbd:`nowcast-green` NEMO-3.6 model runs are computed on a cluster of virtual machines on the `Ocean Networks Canada`_ private cloud computing facility that is part of `west.cloud`_.
   The shared storage for those VMs is provided by an NFS-mounted volume of west.cloud `Ceph object storage`_.
   The nowcast deployment is in the :file:`/nemoShare/MEOPAR/nowcast-sys/` directory tree.

   In April 2017,
   daily :kbd:`wwatch3-forecast2`
   (preliminary wave forecast),
   and :kbd:`wwatch3-forecast` WaveWatch III® v5.16 wave model runs were added to the computations on the ONC cloud.
   They are executed after the :kbd:`forecast2` and :kbd:`forecast` NEMO-3.6 runs.

   .. _Ocean Networks Canada: http://www.oceannetworks.ca/
   .. _west.cloud: https://www.westgrid.ca/support/systems/cc-cloud
   .. _Ceph object storage: https://en.wikipedia.org/wiki/Ceph_(software)

This sections describe the setup of the nowcast system on :kbd:`skookum`/:kbd:`salish` and :kbd:`west.cloud`,
and it operation.

.. toctree::
   :maxdepth: 2

   skookum_salish
   west_cloud
   operations
