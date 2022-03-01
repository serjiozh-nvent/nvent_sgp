## Database auto-generation

The nVent SGP device support module provides a script allowing to generate
EPICS database for specific equipment.

The script communicates over SNMP with an SGP controller, reads out the
required information, and generates device-specific database files.

Alternatively, the script may fetch the required management information from a text file.

### Prerequisites

The auto-generation script requires python version 3 and management tools
provided by net-snmp-utils package (snmpget, snmpwalk).

### Operation details

The script fetches management information using one of the two back-ends:
* NET-SNMP (default)
* text file

The management information consists of sensor-related and control-related data
which is used to form EPICS database records.

Additionally, the script parses naming templates which provide necessary
information on how to translate numerical resource IDs, sensor IDs, and control
IDs into corresponding string literals which constitute resulting EPICS database
record names.

The fetched management information and matching data are used to generate
EPICS database templates and a substitution file.

The template files can then be loaded separately using `dbLoadRecords`, or
as part of the substitution file using `dbLoadTemplate`.

**Examples:**

`dbLoadRecords("sgp-schroff-ttsim-1a.template", "P=SGP:TTSIM1A:,RESID=2000")`

`dbLoadTemplate("sgp.substitutions", "PREFIX=SGP:,HOST=192.168.14.132")`

### Naming templates

The nVent SGP device support module provides several naming templates covering
typical devices included into SGP equipment.

Users are free to modify the existing templates, or create new at their discretion.

Each naming template is a set of records taking one line each. The script recognizes the following record types:

* `name "<pattern>" <id> <file>`  
  Name record is used to match device (resource) name against specified pattern.
  There may be several `name` records in a template.
  No other template records in the template are applicable to a device if
  none of its `name` records matches.
  - `pattern` - a glob pattern to match against device name. See `man 7 glob` for details  
  - `id` - a resource identifier.  
    `id` becomes a part of database record name for all records generated against
    matching device.  
    When matching of two or more devices results in identical `id`, `id` for each
    subsequent device is appended with a number, starting from 2, i.e. for `id=CDU`,
    subsequent device ids are `CDU2, CDU3`, etc.  
  - `file` - a template name where to put generated records.  
    The specified value would be used as a base to form a file name.  
    First, it will be prepended by the database prefix.
    Second, it will be appended with `.template` extension.
    E.g for a name `rackchiller` and database prefix `sgp`, the resulting
    file name is `sgp-rackchiller.template`
* `sensor <num> <id>`  
  Sensor record is used to translate sensor number to an ID, which becomes a
  part of the generated record name.
* `sensor <num> <id>`  
  Control record is used to translate control number to an ID, which becomes a
  part of the generated record name.

### NET-SNMP configuration

While accessing the target device over SNMP, the script relies on the default
NET-SNMP configuration.

See `man snmp.conf` for detailed NET-SNMP configuration description.

The script allows overriding the default SNMP protocol and community string.

### Input text file contents

It is possible to use a file containing pre-fetch SNMP management data instead
of accessing SGP over SNMP.

The script accept `-f` argument which activates file back-end for fetching
the management data.

The management data is expected in the form identical to the output format
when `snmpwalk` or `snmpget` are invoked with `-Oe -Oq` parameters.

### Examples

1. Generate database accessing using SNMPv2 with community string **priv**, prefix output files with **rack1-sgp** and put the output files into **tmp* directory:  
  `./generate-db.py -v 2c -c priv -p rack1-sgp -o tmp 192.168.14.132`
2. Generate database from the file `snmp-vars.txt`, prefix output files with **rack2** and put the output files into current directory:  
  `./generate-db.py -f -p rack2 snmp-vars.txt`
2. Generate database from the file, get naming templates in `~/my-sgp-templates` directory:  
  `./generate-db.py -f -p rack3 -t ~/my-sgp-templates snmp-vars.txt`
