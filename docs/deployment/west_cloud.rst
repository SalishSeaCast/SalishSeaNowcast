.. Copyright 2013-2017 The Salish Sea MEOPAR contributors
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


.. _WestCloudDeployment:

****************************
:kbd:`west.cloud` Deployment
****************************

The `Ocean Networks Canada`_ private cloud computing facility that is part of `west.cloud`_ runs on `OpenStack`_.

.. _Ocean Networks Canada: http://www.oceannetworks.ca/
.. _west.cloud: https://www.westgrid.ca/support/systems/cc-cloud
.. _OpenStack: http://www.openstack.org/

The `OpenStack dashboard`_ provides a web interface to manage and report on cloud resources.
The :kbd:`west.cloud` dashboard is at https://west.cloud.computecanada.ca/dashboard/.

.. _OpenStack dashboard: http://docs.openstack.org/user-guide/content/ch_dashboard.html

Authentication and authorization for :kbd:`west.cloud` is managed by `computecanada`_,
so those are the userid/password that are required to log in to the dashboard.

.. _computecanada: https://www.computecanada.ca/


Web Interface
=============

Initial setup was done via the https://west.cloud.computecanada.ca/dashboard/ web interface with guidance from the
(unpublished at time of writing)
`CC-Cloud Quickstart Guide`_ and the `OpenStack End User Guide`_.

.. _CC-Cloud Quickstart Guide: https://docs.computecanada.ca/wiki/Cloud_Quick_Start
.. _OpenStack End User Guide: http://docs.openstack.org/user-guide/content/openstack_user_guide.html

The project (aka tenant) name for the the Salish Sea NEMO model is :kbd:`NEMO`.


Network
-------

The network configuration was done for us by ONC.
The configuration from the :guilabel:`Network` section of the web interface is recorded here for reference.

Network:

* Network Name: NEMO-network
* Shared: No
* Admin State: Up

Subnet:

* Subnet Name: NEMO-subnet
* Network Address: 192.168.0.0/23
* IP Version: IPv4
* Gateway IP: 192.168.0.1

Subnet Details:

* Enable DHCP: Yes
* IP Allocation Pool: 192.168.0.2 - 192.168.1.254
* DNS Servers: 142.104.6.1 142.104.80.2

Router:

* Router Name: NEMO-gw
* External Network: VLAN3337

Interface:

* Subnet: NEMO-network (NEMO-subnet)
* IP Address: 192.168.0.1
* Router: NEMO-gw


Images
------

An Ubuntu Server 14.04 image was loaded via the :guilabel:`Compute > Images > Create Image` button with the following parameters:

* Name: ubuntu-server-14.04-amd64
* Description: Ubuntu 14.04 64-bit for Salish Sea NEMO project
* Image Source: Image Location
* Image Location: http://cloud-images.ubuntu.com/trusty/current/trusty-server-cloudimg-amd64-disk1.img
* Format: QCOW2 - QEMU Emulator
* Architecture: x86_64
* Minimum Disk (GB): blank
* Minimum RAM (MB): blank
* Public: Yes
* Protected: Yes


Access & Security
-----------------

Generate an ssh key pair on a Linux or OS/X system using the command:

.. code-block:: bash

    $ cd $HOME/.ssh/
    $ ssh -t rsa -f west.cloud_id_rsa -c <yourname>-west.cloud

Assign a strong passphrase to the key pair when prompted.
Passphraseless keys have their place,
but they are a bad idea for general use.

List the public key with the command:

.. code-block:: bash

    $ cat west.cloud_id_rsa.pub

and use copy-paste to import it into the web interface via the :guilabel:`Compute > Access & Security > Key Pairs > Import Key Pair` button.

Use the :guilabel:`Compute > Access & Security > Security Groups > Manage Rules` button associated with the :guilabel:`default` security group to add security rules to allow:

* :command:`ssh`
* :command:`ping`
* ZeroMQ distributed logging subscription

access to the image instances.

:command:`ssh` Rule:

* Rule: SSH
* Remote: CIDR
* CIDR: 0.0.0.0/0

:command:`ping` Rule:

* Rule: ALL ICMP
* Direction: Ingress
* Remote: CIDR
* CIDR: 0.0.0.0/0

ZeroMQ distributed logging subscription Rule:

* Rule: Custom TCP
* Direction: Ingress
* Port range: 5556 - 5557
* Remote: CIDR
* CIDR: 142.103.36.0/24


Instances
---------

Use the :guilabel:`Compute > Instances` section of the web interface to manage instances.

To launch an instance to use as the head node use the :guilabel:`Launch Instance` button.
On the :guilabel:`Details` tab set the following parameters:

* Availability Zone: nova
* Instance Name: nowcast-head-node
* Flavor: nemo-c8-15gb-90
* Instance Count: 1
* Instance Boot Soure: Boot from image
* Image Name: ubuntu-server-14.04-amd64

On the :guilabel:`Access & Security` tab set the following parameters:

* Key Pair: the name of the key pair that you imported
* Security Groups: default enabled

.. note::

    If only 1 key pair has been imported it will be used by default.
    If there is more than 1 key pair available,
    one must be selected.
    Only 1 key can be loaded automatically into an instance on launch.
    Additional public keys can be loaded once an instance is running.

On the :guilabel:`Networking` tab ensure that :guilabel:`NEMO-network` is selected.

Click the :guilabel:`Launch` button to launch the instance.

Once the instance is running use the :guilabel:`More > Associate Floating IP` menu item to associate a public IP address with the instance.


:command:`ssh` Access
=====================

Log in to the publicly accessible instance with the command:

.. code-block:: bash

    $ ssh -i $HOME/.ssh/west.cloud_id_rsa ubuntu@<ip-address>

The first time you connect to an instance you will be prompted to accept its RSA host key fingerprint.
You can verify the fingerprint by looking for the :kbd:`SSH HOST KEY FINGERPRINT` section in the instance log in the :guilabel:`Instances > Instance Details > Log` tab.
If you have previously associated a different instance with th IP address you may receive a message about host key verification failure and potential man-in-the-middle attacks.
To resolve the issue delete the prior host key from your :file:`$HOME/.ssh/known_hosts` file.
The message will tell you what line it is on.

You will also be prompted for the pasphrase that you assigned to the ssh key pair when you created it.
On Linux and OS/X authenticating the ssh key with your pasphrase has the side-effect of adding it to the :command:`ssh-agent` instance that was started when you logged into the system.
You can add the key to the agent yourself with the command:

.. code-block:: bash

    $ ssh-add $HOME/.ssh/west.cloud_id_rsa

You can list the keys that the agent is managing for you with:

.. code-block:: bash

    $ ssh-add -l

You can simplify logins to the instance by adding the following lines to your :file:`$HOME/.ssh/config` file::

  Host west.cloud
      Hostname        <ip-address>
      User            ubuntu
      IdentityFile    ~/.ssh/west.cloud_id_rsa
      ForwardAgent    yes

With that in place you should be able to connect to the instance with:

.. code-block:: bash

    $ ssh west.cloud


Provisioning and Configuration
==============================

Launch an :kbd:`nemo-c8-15gb-90` flavour instance from the :kbd:`ubuntu-server-14.04-amd64` image,
associate a floating IP address with it,
and provision it with the following packages:

.. code-block:: bash

    $ sudo add-apt-repository -y ppa:mercurial-ppa/releases
    $ sudo apt-get update
    $ sudo apt-get install -y mercurial
    $ sudo apt-get install -y gfortran
    $ sudo apt-get install -y libopenmpi1.6 libopenmpi-dev
    $ sudo apt-get install -y openmpi-bin
    $ sudo apt-get install -y libnetcdf-dev netcdf-bin
    $ sudo apt-get install -y libhdf5-dev
    $ sudo apt-get install -y nco
    $ sudo apt-get install -y liburi-perl
    $ sudo apt-get install -y make ksh emacs24
    $ sudo apt-get install -y python-pip python-dev

Use:

.. code-block:: bash

    $ TIMEZONE=Canada/Pacific
    $ sudo timedatectl set-timezone ${TIMEZONE}

to set the timezone.

Set the network interface MTU
(Maximum Transmission Unit)
to 1500 with:

.. code-block:: bash

    $ sudo ip link set dev eth0 mtu 1500

Copy the public key of the passphrase-less ssh key pair that will be used for nowcast cloud operations into :file:`$HOME/.ssh/` and append it to the :file:`authorized_keys` file:

.. code-block:: bash

    # on a system where they key pair is stored
    $ ssh-copy-id -i $HOME/.ssh/SalishSeaNEMO-nowcast_id_rsa.pub west.cloud

The nowcast operations key pair could have been used as the default key pair in the OpenStack web interface,
but using a key pair with a passphrase there allows for more flexibility:
in particular,
the possibliity of revoking the passphrase-less key pair without loosing access to the instances.

Edit :file:`$HOME/.profile` to add code that puts :file:`$HOME/.local/bin` at the front of :envvar:`PATH`:

.. code-block:: bash

    # set PATH so it includes user's private and local bins
    # if they exists
    if [ -d "$HOME/bin" ] ; then
        PATH="$HOME/bin:$PATH"
    fi
    if [ -d "$HOME/.local/bin" ] ; then
        PATH="$HOME/.local/bin:$PATH"
    fi

Create :file:`$HOME/.bash_aliases` containing a command to set the command-line prompt to show the host name and the final directory of the :kbd:`pwd` path,
and to make :command:`rm` default to prompting for confirmation:

.. code-block:: bash

    PS1="\h:\W\$ "

    alias rm="rm -i"




.. _ShareStorageViaNFS:

Shared Storage via NFS
======================

**incomplete**


Mounting Shared Storage on Compute Nodes
----------------------------------------

.. code-block:: bash

    $ sudo mkdir -p /nemoShare/MEOPAR
    $ sudo chown ubuntu:ubuntu /nemoShare/MEOPAR
    $ sudo mount HeadNodeIP:/MEOPAR /nemoShare/MEOPAR

where :kbd:`HeadNodeIP` is the internal cloud network IP address of the head node where the NFS server is running;
e.g.

.. code-block:: bash

    $ sudo mount 192.168.1.53:/MEOPAR /nemoShare/MEOPAR

.. note::
    The :file:`/nemoShare/MEOPAR` shared storage must be remounted any time a compute node is rebooted or if the :kbd:`west.cloud` system administrators move it from one hypervisor to another.


Mercurial Repositories
======================

Clone the following repos into :file:`/nemoShare/MEOPAR/nowcast-sys/`:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/
    $ hg clone --ssh "ssh -i ~/.ssh/salishsea-nowcast-deployment_id_rsa.pub" ssh://hg@bitbucket.org/salishsea/salishseawaves SalishSeaWaves


.. _BuildWaveWatch3:

Build WAVEWATCH III :sup:`®`
============================

Access to download WAVEWATCH III :sup:`®`
(ww3 hereafter)
code tarballs is obtained by sending an email request from the http://polar.ncep.noaa.gov/waves/wavewatch/license.shtml.
The eventual reply will provide a username and password that can be used to access http://polar.ncep.noaa.gov/waves/wavewatch/distribution/ from which the :file:`wwatch3.v5.16.tar.gz` files can be downloaded with:

.. code-block:: bash

    $ curl -u username:password -LO download_url

where :kbd:`username`,
:kbd:`password`,
and :kbd:`download_url` are those provided in the reply to the email request.

.. note::
    The `west.cloud-vm`_ repo provides a `Vagrant`_ virtual machine configuration that emulates the Salish Sea Nowcast system compute deployment on ONC west.cloud VMs.
    The VM can be used for small scale testing of ww3.

    .. _west.cloud-vm: https://bitbucket.org/salishsea/west.cloud-vm
    .. _Vagrant: https://www.vagrantup.com/

Follow the instructions in the Installing Files section of the `ww3 manual`_ to unpack the tarball to create a local installation in :file:`/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/`
that will use the :program:`gfortran` and :program:`gcc` compilers:

.. _ww3 manual: http://polar.ncep.noaa.gov/waves/wavewatch/manual.v5.16.pdf

.. code-block:: bash

    $ mkdir /nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16
    $ cd /nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16
    $ tar -xvzf wwatch3.v5.16.tar.gz
    $ ./install_ww3_tar

:program:`install_ww3_tar` is an interactive shell script.
Accept the defaults that it offers other than to choose:

* local installation in :file:`/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/`
* :program:`gfortran` as the Fortran 77 compiler
* :program:`gcc` as the C compiler

Add code to :file:`$HOME/.profile` to add :file:`/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/bin` and :file:`/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/exe` to :envvar:`PATH`:

.. code-block:: bash

    # Add wwatch3 bin/ and exe/ paths to PATH if they exist
    if [ -d "/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/bin" ] ; then
        PATH="/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/bin:$PATH"
    fi
    if [ -d "/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/exe" ] ; then
        PATH="/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/exe:$PATH"
    fi

Change the :file:`comp` and :file:`link` scripts in :file:`/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/bin` to point to :file:`comp.gnu` and :file:`link.gnu`,
and make :file:`comp.gnu` executable:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/bin
    $ ln -sf comp.gnu comp && chmod +x comp.gnu
    $ ln -sf link.gnu link

Symlink the :file:`SalishSeaWaves/switch` file in :file:`/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/bin`:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/bin
    $ ln -sf /nemoShare/MEOPAR/nowcast-sys/SalishSeaWaves/switch switch

Add code to :file:`$HOME/.profile` to set the :envvar:`WWATCH3_NETCDF` and :envvar:`NETCDF_CONFIG` environment variables:

.. code-block:: bash

# Enable wwatch3 to use netCDF4
export WWATCH3_NETCDF=NC4
export NETCDF_CONFIG=$(which nc-config)

Build the suite of ww3 programs with:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/work
    $ w3_make


WaveWatch Runs Directories
==========================

Create a :file:`wwatch3-runs` directory tree and populate it with:

* The wwatch3 grid:

  .. code-block:: bash

      $ mkdir -p /nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/grid
      $ cd /nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/
      $ ln -s /nemoShare/MEOPAR/nowcast-sys/SalishSeaWaves/ww3_grid_SoG.inp ww3_grid.inp
      $ cd /nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/grid
      $ ln -sf /nemoShare/MEOPAR/nowcast-sys/SalishSeaWaves/SoG_BCgrid_00500m.bot
      $ ln -sf /nemoShare/MEOPAR/nowcast-sys/SalishSeaWaves/SoG_BCgrid_00500m.msk
      $ cd /nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/
      $ ww3_grid | tee ww3_grid.out

* Directory and wwatch3 :file:`.inp` file for wind forcing:

  .. code-block:: bash

      $ mkdir -p /nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/wind
      $ cp /nemoShare/MEOPAR/nowcast-sys/SalishSeaWaves/ww3_prnc_wind.inp /nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/

  The :program:`run_wwatch3` worker will:

  * edit the wind forcing file path(s) for each run into :file:`ww3_prnc_wind.inp`
  * symlink :file:`ww3_prnc_wind.inp` as :file:`ww3_prnc.inp`
  * run :program:`ww3_prnc` to produce the wwatch3 wind forcing files for the run,
    storing its output in :file:`ww3_prnc_wind.out`

* Directory and wwatch3 :file:`.inp` file for current forcing:

  .. code-block:: bash

      $ mkdir -p /nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/current
      $ cp  /nemoShare/MEOPAR/nowcast-sys/SalishSeaWaves/ww3_prnc_current.inp /nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/

  The :program:`run_wwatch3` worker will:

  * edit the current forcing file path(s) for each run into :file:`ww3_prnc_current.inp`
  * symlink :file:`ww3_prnc_current.inp` as :file:`ww3_prnc.inp`
  * run :program:`ww3_prnc` to produce the wwatch3 current forcing files for the run,
    storing its output in :file:`ww3_prnc_current.out`

* The wwatch3 shell :file:`.inp` file:

  .. code-block:: bash

      $ cp  /nemoShare/MEOPAR/nowcast-sys/SalishSeaWaves/ww3_shel.inp /nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/

  The :program:`run_wwatch3` worker will:

  * edit the start and end dates/times for each run into :file:`ww3_shel.inp`
  * run :program:`ww3_shel` to execute the wwatch3 run
