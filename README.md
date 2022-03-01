## nvent_sgp

nVent Smart Gateway Platform (SGP) support module based on snmp communication protocol.

### Provides

* A standalone application for providing an IOC with SGP database
* A pre-generated sample database for a SGP device
* A set of pre-generated database templates covering packaged components
* A database auto-generation script for generated customized templates against specific device
* A dockerfile to setup EPICS/ESS environment for running SGP IOC on a host machine for testing purposes

### Module dependencies

1. epics-base  
 The project is tested against epics-base/7.0.5.
1. snmp  
 The module requires snmp revision 1.1.0.3

### Building and running

1. Edit `configure/RELEASE` or create `configure/RELEASE.local` to set up
   paths to dependent modules.
1. Run `make all`.
1. Edit `iocBoot/iocSgp/st.cmd` to setup SGP's `HOSTNAME` and other parameters.
1. Invoke `iocsh`  
   `cd iocBoot/iocSgp`  
   `../../bin/linux-x86_64/sgp st.cmd`

### Auto-generate database

Refer to `scripts/README.md` for details.
