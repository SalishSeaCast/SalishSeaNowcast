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
    $ sudo add-apt-repository -y ppa:git-core/ppa
    $ sudo apt-get update
    $ sudo apt-get install -y mercurial git
    $ sudo apt-get install -y gfortran
    $ sudo apt-get install -y libopenmpi1.6 libopenmpi-dev
    $ sudo apt-get install -y openmpi-bin
    $ sudo apt-get install -y libnetcdf-dev netcdf-bin
    $ sudo apt-get install -y libhdf5-dev
    $ sudo apt-get install -y nco
    $ sudo apt-get install -y liburi-perl m4
    $ sudo apt-get install -y make ksh emacs24
    $ sudo apt-get install -y python-pip python-dev
    $ sudo apt-get install -y nfs-common

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
the possibility of revoking the passphrase-less key pair without loosing access to the instances.

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

Also add code to :file:`$HOME/.profile` to add wwatch3 :file:`bin/` and :file:`exe/` paths to :envvar:`PATH` if they exist,
and export environment variables to enable wwatch3 to use netCDF4:

.. code-block:: bash

    # Add wwatch3 bin/ and exe/ paths to PATH if they exist
    if [ -d "/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/bin" ] ; then
        PATH="/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/bin:$PATH"
    fi
    if [ -d "/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/exe" ] ; then
        PATH="/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/exe:$PATH"
    fi

    # Enable wwatch3 to use netCDF4
    export WWATCH3_NETCDF=NC4
    export NETCDF_CONFIG=$(which nc-config)

Create :file:`$HOME/.bash_aliases` containing a command to set the command-line prompt to show the host name and the final directory of the :kbd:`pwd` path,
and to make :command:`rm` default to prompting for confirmation:

.. code-block:: bash

    PS1="\h:\W\$ "

    alias rm="rm -i"


.. _HeadNodeSanpshotImage:

Head Node Snapshot Image
------------------------

Use the OpenStack web interface to create a snapshot of the instance for use as the "head" node for running the nowcast system.
The head node is the one that will have the public IP address associated with it and it will be used for commands,
uploads,
and downloads.
It is also used as to run the XIOS server process for NEMO runs.


.. _ComputeNodeSanpshotImage:

Compute Node Snapshot Image
---------------------------

On an instance launched from the :ref:`HeadNodeSanpshotImage` remove the :file:`$HOME/.local/bin/` directory:

.. code-block:: bash

    $ rm -rf $HOME/.local

Remove :file:`$HOME/.local/` from :envvar:`PATH`:

.. code-block:: bash

    export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games

Use the OpenStack web interface to create a snapshot of the instance for use as compute nodes for running the nowcast system NEMO and WAVEWATCH  III :sup:`®` runs.
Compute nodes provide cores and RAM for the runs.


.. _ShareStorageViaNFS:

Shared Storage via NFS
======================

Shared storage for the nodes is provided from the `Westgrid Arbutus`_ cluster `Ceph`_ object storage system.
A 1 Tb block of storage is mounted on the :kbd:`nowcast0` head node at :file:`/nemoShare/MEOPAR/`.
As described in the sections below,
the head node is configured as an NFS server to provide access to this storage via NFS mounts on the compute nodes.

.. _Westgrid Arbutus: https://docs.computecanada.ca/wiki/CC-Cloud_Resources
.. _Ceph: https://en.wikipedia.org/wiki/Ceph_(software)


NFS Server for Shared Storage on Head Node
------------------------------------------

Reference: https://help.ubuntu.com/community/SettingUpNFSHowTo

.. code-block:: bash

    $ sudo apt-get install nfs-kernel-server
    $ sudo mkdir -p /export/MEOPAR
    $ sudo chmod 777 /export/ /export/MEOPAR/
    $ sudo mount --bind /nemoShare/MEOPAR /export/MEOPAR

Add the following line to :file:`/etc/fstab`::

  /nemoShare/MEOPAR   /export/MEOPAR  none  bind  0  0

Add the following 2 line2 to :file:`/etc/exports`::

  /export        192.168.1.0/24(rw,fsid=0,insecure,no_subtree_check,async)
  /export/MEOPAR 192.168.1.0/24(rw,nohide,insecure,no_subtree_check,async)

Restart the NFS service:

  .. code-block:: bash

    $ sudo service nfs-kernel-server restart


Mounting Shared Storage on Compute Nodes
----------------------------------------

Reference: https://help.ubuntu.com/community/SettingUpNFSHowTo

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
    $ hg clone ssh://hg@bitbucket.org/mdunphy/fvcom-cmd FVCOM-Cmd
    $ hg clone ssh://hg@bitbucket.org/salishsea/grid grid
    $ hg clone --ssh "ssh -i ~/.ssh/salishsea-nowcast-deployment_id_rsa.pub" ssh://hg@bitbucket.org/salishsea/nemo-3.6-code NEMO-3.6-code
    $ hg clone ssh://hg@bitbucket.org/salishsea/nemo-cmd NEMO-Cmd
    $ hg clone ssh://hg@bitbucket.org/43ravens/nemo_nowcast NEMO_Nowcast
    $ hg clone ssh://hg@bitbucket.org/salishsea/rivers-climatology rivers-climatology
    $ hg clone ssh://hg@bitbucket.org/salishsea/salishseacmd SalishSeaCmd
    $ hg clone ssh://hg@bitbucket.org/salishsea/salishseanowcast SalishSeaNowcast
    $ hg clone ssh://hg@bitbucket.org/salishsea/salishseawaves SalishSeaWaves
    $ hg clone ssh://hg@bitbucket.org/salishsea/ss-run-sets SS-run-sets
    $ hg clone ssh://hg@bitbucket.org/salishsea/tides tides
    $ hg clone ssh://hg@bitbucket.org/salishsea/tools tools
    $ hg clone ssh://hg@bitbucket.org/salishsea/tracers tracers
    $ hg clone --ssh "ssh -i ~/.ssh/salishsea-nowcast-deployment_id_rsa.pub" ssh://hg@bitbucket.org/salishsea/xios-2 XIOS-2
    $ hg clone ssh://hg@bitbucket.org/salishsea/xios-arch XIOS-ARCH


Git Repositories
================

Clone the following repos into :file:`/nemoShare/MEOPAR/nowcast-sys/`:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/
    $ git clone git@gitlab.com:mdunphy/FVCOM-VHFR-config.git
    $ git clone git@gitlab.com:mdunphy/OPPTools.git OPPTools


Build XIOS-2
============

Symlink the XIOS-2 build configuration files for :kbd:`west.cloud` from the :file:`XIOS-ARCH` repo clone into the :file:`XIOS-2/arch/` directory:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/XIOS-2/arch
    $ ln -s ../../XIOS-ARCH/WEST.CLOUD/arch-GCC_NOWCAST.fcm
    $ ln -s ../../XIOS-ARCH/WEST.CLOUD/arch-GCC_NOWCAST.path

Build XIOS-2 with:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/XIOS-2
    $ ./make_xios --arch GCC_NOWCAST --netcdf_lib netcdf4_seq --job 8


Build NEMO-3.6
==============

Build NEMO-3.6 and :program:`rebuild_nemo.exe`:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/NEMO-3.6-code/NEMOGCM/CONFIG
    $ XIOS_HOME=/nemoShare/MEOPAR/nowcast-sys/XIOS-2 ./makenemo -m GCC_NOWCAST -n SalishSea -j8
    $ cd /nemoShare/MEOPAR/nowcast-sys/NEMO-3.6-code/NEMOGCM/TOOLS/
    $ ./maketools -m GCC_NOWCAST_REBUILD_NEMO -n REBUILD_NEMO


.. _BuildWaveWatch3:

Build WAVEWATCH III :sup:`®`
============================

Access to download WAVEWATCH III :sup:`®`
(wwatch3 hereafter)
code tarballs is obtained by sending an email request from the http://polar.ncep.noaa.gov/waves/wavewatch/license.shtml.
The eventual reply will provide a username and password that can be used to access http://polar.ncep.noaa.gov/waves/wavewatch/distribution/ from which the :file:`wwatch3.v5.16.tar.gz` files can be downloaded with:

.. code-block:: bash

    $ curl -u username:password -LO download_url

where :kbd:`username`,
:kbd:`password`,
and :kbd:`download_url` are those provided in the reply to the email request.

.. note::
    The `west.cloud-vm`_ repo provides a `Vagrant`_ virtual machine configuration that emulates the Salish Sea Nowcast system compute deployment on ONC west.cloud VMs.
    The VM can be used for small scale testing of wwatch3.

    .. _west.cloud-vm: https://bitbucket.org/salishsea/west.cloud-vm
    .. _Vagrant: https://www.vagrantup.com/

Follow the instructions in the Installing Files section of the `wwatch3 manual`_ to unpack the tarball to create a local installation in :file:`/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/`
that will use the :program:`gfortran` and :program:`gcc` compilers:

.. _wwatch3 manual: http://polar.ncep.noaa.gov/waves/wavewatch/manual.v5.16.pdf

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

Ensure that :file:`/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/bin` and :file:`/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/exe` are in :envvar:`PATH`.

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

Export the :envvar:`WWATCH3_NETCDF` and :envvar:`NETCDF_CONFIG` environment variables:

.. code-block:: bash

    export WWATCH3_NETCDF=NC4
    export NETCDF_CONFIG=$(which nc-config)

Build the suite of wwatch3 programs with:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/work
    $ w3_make


.. _BuildFVCOM41:

Build FVCOM-4.1
===============

Clone the FVCOM-4.1 repo into :file:`/nemoShare/MEOPAR/nowcast-sys/`:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/
    $ ssh-agent bash -c 'ssh-add ~/.ssh/salishsea-nowcast-deployment_id_rsa; git clone git@gitlab.com:mdunphy/FVCOM41.git FVCOM41'

Hard-coded :envvar:`TOPDIR` paths in the FVCOM configuration and build scripts expect the source tree to the at :file:`$HOME/OPP/FVCOM41.git`,
so make that so via symlinks:

.. code-block:: bash

    $ cd $HOME
    $ sudo mkdir /nemoShare/OPP
    $ sudo chown ubuntu:ubuntu /nemoShare/OPP
    $ ln -s /nemoShare/OPP
    $ ln -s /nemoShare/MEOPAR/nowcast-sys/FVCOM41 /nemoShare/OPP/FVCOM41.git

Build FVCOM with:

.. code-block:: bash

    $ cd $HOME/OPP/FVCOM41.git/Configure
    $ ./setup -a UBUNTU-14.04-GCC -c VancouverHarbourV2
    $ ./build -l –f


.. _UpdateFVCOM41:

Update FVCOM-4.1
----------------

Fetch and merge changes from the `FVCOM41 repo on GitLab`_ and do a clean build:

.. _FVCOM41 repo on GitLab: https://gitlab.com/mdunphy/FVCOM41

.. code-block:: bash

    $ cd $HOME/OPP/FVCOM41.git/
    $ git pull origin master
    $ cd Configure/
    $ ./setup -a UBUNTU-14.04-GCC -c VancouverHarbourV2
    $ ./build -l –f


Python Packages
===============

The Python packages that the system depends on are installed in a conda environment with:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/
    $ conda update conda
    $ conda create \
        --prefix /nemoShare/MEOPAR/nowcast-sys/nowcast-env \
        --channel gomss-nowcast --channel conda-forge --channel defaults \
        arrow attrs basemap beautifulsoup4 bottleneck circus cliff cmocean \
        dask docutils lxml mako matplotlib=1.5.3 netcdf4 numpy pandas paramiko \
        pillow pip python=3.6 pyyaml pyzmq requests schedule scipy shapely xarray
    $ source /nemoShare/MEOPAR/nowcast-sys/nemo_nowcast-env/bin/activate /nemoShare/MEOPAR/nowcast-sys/nemo_nowcast-env/
    (/nemoShare/MEOPAR/nowcast-sys/nowcast-env)$ pip install angles driftwood \
        f90nml feedgen python-hglib raven retrying scour utm
    (/nemoShare/MEOPAR/nowcast-sys/nemo_nowcast-env)$ pip install --editable NEMO_Nowcast/
    (/nemoShare/MEOPAR/nowcast-sys/nemo_nowcast-env)$ pip install --editable tools/SalishSeaTools/
    (/results/nowcast-sys/nowcast-env)$ pip install --editable OPPTools/
    (/nemoShare/MEOPAR/nowcast-sys/nemo_nowcast-env)$ pip install --editable NEMO-Cmd/
    (/nemoShare/MEOPAR/nowcast-sys/nemo_nowcast-env)$ pip install --editable SalishSeaCmd/
    (/nemoShare/MEOPAR/nowcast-sys/nemo_nowcast-env)$ pip install --editable FVCOM-Cmd/
    (/nemoShare/MEOPAR/nowcast-sys/nemo_nowcast-env)$ pip install --editable SalishSeaNowcast/


Environment Variables
=====================

Add the following files to the :file:`/nemoShare/MEOPAR/nowcast-sys/nowcast-env` environment to automatically :command:`export` the environment variables required by the nowcast system when the environment is activated:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/nowcast-env
    $ mkdir -p etc/conda/activate.d
    $ cat << EOF > etc/conda/activate.d/envvars.sh
    export NOWCAST_ENV=/nemoShare/MEOPAR/nowcast-sys/nowcast-env
    export NOWCAST_CONFIG=/nemoShare/MEOPAR/nowcast-sys/SalishSeaNowcast/config
    export NOWCAST_YAML=/nemoShare/MEOPAR/nowcast-sys/SalishSeaNowcast/config/nowcast.yaml
    export NOWCAST_LOGS=/nemoShare/MEOPAR/nowcast-sys/logs/nowcast
    export SENTRY_DSN=a_valid_sentry_dsn_url
    EOF

and :command:`unset` them when it is deactivated.

.. code-block:: bash

    $ mkdir -p etc/conda/deactivate.d
    $ cat << EOF > etc/conda/deactivate.d/envvars.sh
    unset NOWCAST_ENV
    unset NOWCAST_CONFIG
    unset NOWCAST_YAML
    unset NOWCAST_LOGS
    unset SENTRY_DSN
    EOF


.. _WestCloudNowcastRunsDirectory:

Nowcast Runs Directory
======================

Create a :file:`runs/` directory for the NEMO runs and populate it with:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/
    $ mkdir runs
    $ chmod g+ws runs
    $ cd runs/
    $ mkdir -p LiveOcean NEMO-atmos rivers ssh
    $ chmod -R g+s LiveOcean NEMO-atmos rivers ssh
    $ cp ../SS-run-sets/v201702/nowcast-green/namelist.time_nowcast_template namelist.time


WaveWatch Runs Directories
==========================

Create a :file:`wwatch3-runs/` directory tree and populate it with:

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

* Directory for wind forcing:

  .. code-block:: bash

      $ mkdir -p /nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/wind

  The :program:`make_ww3_wind_file` worker:

  * Uses files from :file:`/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/` appropriate for the wwatch3 run date and type to produce a :file:`SoG_wind_yyyymmdd.nc` file in the :file:`wind/` directory

  The :program:`run_ww3` worker:

  * Generates in the temporary run directory a :file:`ww3_prnc_wind.inp` file containing the path to the file produced by the :program:`make_ww3_wind_file` worker
  * Symlinks :file:`ww3_prnc_wind.inp` as :file:`ww3_prnc.inp`
  * Runs :program:`ww3_prnc` to produce the wwatch3 wind forcing files for the run.
    The output of :program:`ww3_prnc` is stored in the run's :file:`stdout` file.

* Directory for current forcing:

  .. code-block:: bash

      $ mkdir -p /nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/current

  The :program:`make_ww3_wind_file` worker:

  * Uses files from the :file:`/nemoShare/MEOPAR/SalishSea/` NEMO results storage tree appropriate for the wwatch3 run date and type to produce a :file:`SoG_current_yyyymmdd.nc` file in the :file:`current/` directory

  The :program:`run_ww3` worker:

  * Generates in the temporary run directory a :file:`ww3_prnc_current.inp` file containing the path to the file produced by the :program:`make_ww3_current_file` worker
  * Symlinks :file:`ww3_prnc_current.inp` as :file:`ww3_prnc.inp`
  * Runs :program:`ww3_prnc` to produce the wwatch3 current forcing files for the run.
    The output of :program:`ww3_prnc` is stored in the run's :file:`stdout` file.
