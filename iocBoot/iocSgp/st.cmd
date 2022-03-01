###############################################################################
# Set up environment
iocshLoad("envPaths")
epicsEnvSet("HOSTNAME", "80.240.102.61")
epicsEnvSet("P","$(P=SGP)")
epicsEnvSet("IOC","$(IOC=IOC-$(P))")
epicsEnvSet("MIBDIRS", "+$(TOP)/mibs")
devSnmpSetParam(SetSkipReadbackMSec, 6000)
devSnmpSetParam(PassivePollMSec, 120000)
devSnmpSetParam(DataStaleTimeoutMSec, 120000)
devSnmpSetParam(SessionRetries, 1)
devSnmpSetSnmpVersion("$(HOSTNAME)", SNMP_VERSION_2c)
devSnmpSetMaxOidsPerReq("$(HOSTNAME)", $(MAXOIDS=12))

# uncomment to be verbose
#devSnmpSetParam("DebugLevel",100)

###############################################################################
# Register all support components
cd "${TOP}"
dbLoadDatabase "dbd/sgp.dbd"
sgp_registerRecordDeviceDriver pdbbase

###############################################################################
# Load record instances
dbLoadRecords("db/sgp.db","PREFIX=$(P),HOST=$(HOSTNAME),USER_R=public,USER_W=private")

###############################################################################
# Start EPICS
cd "${TOP}/iocBoot/${IOC}"
iocInit
