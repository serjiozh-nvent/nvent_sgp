TOP=../..

include $(TOP)/configure/CONFIG
#----------------------------------------
#  ADD MACRO DEFINITIONS AFTER THIS LINE
#=============================

#=============================
# Build the IOC application

PROD_IOC =sgp

#
# Pick up the net-snmp support
#
USR_CFLAGS += `net-snmp-config --cflags`
USR_LDFLAGS += `net-snmp-config --libs`
PROD_LDLIBS += `net-snmp-config --libs`

# sgp.dbd will be created and installed
DBD += sgp.dbd

# sgp.dbd will be made up from these files:
sgp_DBD += base.dbd devSnmp.dbd

# Build the main IOC entry point on workstation OSs.
sgp_SRCS_DEFAULT += main.cpp
sgp_SRCS_vxWorks += -nil-

# sgp_registerRecordDeviceDriver.cpp derives from sgp.dbd
sgp_SRCS += sgp_registerRecordDeviceDriver.cpp

# Add all the support libraries needed by this IOC
sgp_LIBS += devSnmp

# Finally link to the EPICS Base libraries
sgp_LIBS += $(EPICS_BASE_IOC_LIBS)

#===========================

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD RULES AFTER THIS LINE
