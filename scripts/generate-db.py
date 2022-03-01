#!/usr/bin/env python3
import argparse
import enum
import fnmatch
import io
import os
import re
import sys


class Logger:
    def __init__(self, level):
        self.level = level

    def log(self, level, line):
        if level <= self.level:
            print(line)

    def error(self, line):
        self.log(0, line)

    def info(self, line):
        self.log(1, line)

    def verbose(self, line):
        self.log(2, line)

    def debug(self, line):
        self.log(3, line)


class TypeSensorUnit(enum.IntEnum):
    unspecified = -1
    degreesC = 1
    degreesF = 2
    degreesK = 3
    volts = 4
    amps = 5
    watts = 6
    joules = 7
    coulombs = 8
    va = 9
    nits = 10
    lumen = 11
    lux = 12
    candela = 13
    kpa = 14
    psi = 15
    newton = 16
    cfm = 17
    rpm = 18
    hz = 19
    microsecond = 20
    millisecond = 21
    second = 22
    minute = 23
    hour = 24
    day = 25
    week = 26
    mil = 27
    inches = 28
    feet = 29
    cuIn = 30
    cuFeet = 31
    mm = 32
    cm = 33
    m = 34
    cuCm = 35
    cuM = 36
    liters = 37
    fluidOunce = 38
    radians = 39
    steradians = 40
    revolutions = 41
    cycles = 42
    gravities = 43
    ounce = 44
    pound = 45
    ftLb = 46
    ozIn = 47
    gauss = 48
    gilberts = 49
    henry = 50
    millihenry = 51
    farad = 52
    microfarad = 53
    ohms = 54
    siemens = 55
    mole = 56
    becquerel = 57
    ppm = 58
    reserved = 59
    decibels = 60
    dba = 61
    dbc = 62
    gray = 63
    sievert = 64
    colorTempDegK = 65
    bit = 66
    kilobit = 67
    megabit = 68
    gigabit = 69
    byte = 70
    kilobyte = 71
    megabyte = 72
    gigabyte = 73
    word = 74
    dword = 75
    qword = 76
    line = 77
    hit = 78
    miss = 79
    retry = 80
    reset = 81
    overrun = 82
    underrun = 83
    collision = 84
    packets = 85
    messages = 86
    characters = 87
    errors = 88
    correctableErrors = 89
    uncorrectableErrors = 90


class SnmpBackend:
    def __init__(self, logger, host, proto, comm):
        self.logger = logger
        self.host = host
        if proto:
            self.logger.debug("Using protocol version %s" % proto)
            self.protostr = "-v %s" % proto
        else:
            self.logger.debug("Using default protocol version")
            self.protostr = ""
        if comm:
            self.logger.debug("Using community string %s" % comm)
            self.commstr = "-c %s" % comm
        else:
            self.logger.debug("Using default community string")
            self.commstr = ""
        os.environ["MIBDIRS"] = "+../mibs"

    def __subprocess(self, cmd, oid):
        cmdstr = "%s %s %s -Oe -Oq %s %s" % (
            cmd,
            self.protostr,
            self.commstr,
            self.host,
            oid,
        )
        self.logger.debug("SNMP: %s" % cmdstr)
        return os.popen(cmdstr)

    def get(self, oid):
        with self.__subprocess("snmpget", oid) as p:
            out = p.read()
            self.logger.debug("SNMP: %s" % out)
        return out

    def walk(self, oid):
        out = []
        with self.__subprocess("snmpwalk", oid) as p:
            while True:
                line = p.readline()
                if not line:
                    break
                self.logger.debug("SNMP: %s" % line)
                out += [line]
        return out


class FileBackend:
    def __init__(self, logger, path):
        self.logger = logger
        self.logger.info("Using %s for retrieving data" % path)
        with open(path, "rt") as fd:
            self.vars = fd.read()

    def get(self, oid):
        with io.StringIO(self.vars) as fd:
            while True:
                line = fd.readline()
                if not line:
                    break
                if line.startswith(oid):
                    self.logger.debug("SNMP: %s" % line)
                    return line
        return None

    def walk(self, oid):
        out = []
        with io.StringIO(self.vars) as fd:
            while True:
                line = fd.readline()
                if not line:
                    break
                if line.startswith(oid):
                    self.logger.debug("SNMP: %s" % line)
                    out += [line]
        return out


class SnmpClient:
    def __init__(self, backend):
        self.backend = backend

    def query_sensors(self):
        return self.backend.walk("SGP-MIB::externalSensorName")

    def query_controls(self):
        return self.backend.walk("SGP-MIB::ctrlName")

    def query_value(self, oid):
        line = self.backend.get(oid)
        if line:
            return line.split()[1]
        return None

    def query_resource_name(self, res, id):
        line = self.backend.get("SGP-MIB::externalResourceName.%s.%s" % (res, id))
        frags = line.split()
        return " ".join(frags[1:])

    def query_sensor_is_threshold(self, res, id):
        return (
            self.query_value("SGP-MIB::externalSensorCategory.%s.%s" % (res, id)) == "1"
        )

    def query_thresholds_is_accessible(self, res, id):
        return (
            self.query_value(
                "SGP-MIB::externalSensorThresholdsIsAccessible.%s.%s" % (res, id)
            )
            == "1"
        )

    def query_reading_is_available(self, res, id):
        return (
            self.query_value(
                "SGP-MIB::externalSensorIsReadingSupported.%s.%s" % (res, id)
            )
            == "1"
        )

    def query_sensor_resolution(self, res, id):
        return float(
            self.query_value("SGP-MIB::externalSensorResolution.%s.%s" % (res, id))
        )

    def query_sensor_thresholds(self, res, id):
        lct = self.query_value(
            "SGP-MIB::externalSensorLowerCriticalThreshold.%s.%s" % (res, id)
        )
        lmj = self.query_value(
            "SGP-MIB::externalSensorLowerMajorThreshold.%s.%s" % (res, id)
        )
        lmn = self.query_value(
            "SGP-MIB::externalSensorLowerMinorThreshold.%s.%s" % (res, id)
        )
        uct = self.query_value(
            "SGP-MIB::externalSensorUpperCriticalThreshold.%s.%s" % (res, id)
        )
        umj = self.query_value(
            "SGP-MIB::externalSensorUpperMajorThreshold.%s.%s" % (res, id)
        )
        umn = self.query_value(
            "SGP-MIB::externalSensorUpperMinorThreshold.%s.%s" % (res, id)
        )
        return (lct, lmj, lmn, uct, umj, umn)

    def query_sensor_limits(self, res, id):
        min = self.query_value("SGP-MIB::externalSensorMinimum.%s.%s" % (res, id))
        max = self.query_value("SGP-MIB::externalSensorMaximum.%s.%s" % (res, id))
        return (min, max)

    def query_sensor_egu(self, res, id):
        base = TypeSensorUnit(
            int(self.query_value("SGP-MIB::externalSensorBaseUnit.%s.%s" % (res, id)))
        ).name
        use = self.query_value("SGP-MIB::externalSensorModifierUse.%s.%s" % (res, id))
        if use != "-1":
            mod = TypeSensorUnit(
                int(
                    self.query_value(
                        "SGP-MIB::externalSensorModifierUnit.%s.%s" % (res, id)
                    )
                )
            ).name
            if use == "1":
                base += "/" + mod
            else:
                base += "*" + mod
        return base

    def query_control_limits(self, res, id):
        min = self.query_value("SGP-MIB::ctrlMinimumValue.%s.%s" % (res, id))
        max = self.query_value("SGP-MIB::ctrlMaximumValue.%s.%s" % (res, id))
        return (min, max)


class SensorInfo:
    def __init__(self, line):
        frag = line.split()
        frag2 = frag[0].split(".")
        desc = " ".join(frag[1:])
        # fill-in defaults
        self.res = frag2[1]
        self.id = frag2[2]
        self.desc = desc
        self.lct = "N/A"
        self.lmj = "N/A"
        self.lmn = "N/A"
        self.uct = "N/A"
        self.umj = "N/A"
        self.umn = "N/A"
        self.min = "N/A"
        self.max = "N/A"
        self.state = True
        self.prec = 0

    def __eq__(self, other):
        return self.id == other.id and self.desc == other.desc


class ControlInfo:
    def __init__(self, line):
        frag = line.split()
        frag2 = frag[0].split(".")
        desc = " ".join(frag[1:])
        # fill-in defaults
        self.res = frag2[1]
        self.id = frag2[2]
        self.desc = desc
        self.min = "N/A"
        self.max = "N/A"

    def __eq__(self, other):
        return self.id == other.id and self.desc == other.desc


class ResourceInfo:
    def __init__(self, desc):
        #        self.id = id
        self.desc = desc
        self.sensors = []
        self.controls = []

    def __eq__(self, other):
        return self.sensors == other.sensors and self.control == other.controls


class ResourceInfoFetcher:
    def __init__(self, logger, backend):
        self.logger = logger
        self.client = SnmpClient(backend)
        self.map = {}

    def __create_resource(self, res, desc):
        # create resource mapping
        resource = ResourceInfo(desc)

        self.logger.verbose("Created resourse:")
        self.logger.verbose("  Res:  %s" % res)
        self.logger.verbose("  Desc:  %s" % desc)

        self.map[res] = resource
        return resource

    def __fetch_sensor(self, sensor):
        self.logger.verbose(
            "Fetching sensor data %s.%s %s" % (sensor.res, sensor.id, sensor.desc)
        )

        try:
            # get existing resource
            resource = self.map[sensor.res]
        except KeyError:
            # create new resource
            resource = self.__create_resource(
                sensor.res, self.client.query_resource_name(sensor.res, sensor.id)
            )

        # check if sensor is threshold
        if self.client.query_thresholds_is_accessible(sensor.res, sensor.id):
            # query sensor thresholds
            (
                sensor.lct,
                sensor.lmj,
                sensor.lmn,
                sensor.uct,
                sensor.umj,
                sensor.umn,
            ) = self.client.query_sensor_thresholds(sensor.res, sensor.id)

        # query sensor limits
        sensor.min, sensor.max = self.client.query_sensor_limits(sensor.res, sensor.id)

        # query sensor units
        sensor.egu = self.client.query_sensor_egu(sensor.res, sensor.id)

        # check if sensor reading is supported
        sensor.state = not self.client.query_reading_is_available(sensor.res, sensor.id)

        # check if sensor is integer
        if sensor.state == False:
            sensor.prec = self.client.query_sensor_resolution(sensor.res, sensor.id)

        # dump gathered info
        self.logger.verbose("  Res:  %s" % sensor.res)
        self.logger.verbose("  Id:   %s" % sensor.id)
        self.logger.verbose("  Desc: %s" % sensor.desc)
        self.logger.verbose(
            "  Lower thresholds: %s %s %s" % (sensor.lct, sensor.lmj, sensor.lmn)
        )
        self.logger.verbose(
            "  Upper thresholds: %s %s %s" % (sensor.uct, sensor.umj, sensor.umn)
        )
        self.logger.verbose("  Limits: %s %s" % (sensor.min, sensor.max))
        self.logger.verbose("  EGU: %s" % sensor.egu)
        self.logger.verbose("  PREC: %s" % sensor.prec)

        # add to list
        resource.sensors += [sensor]

    def __fetch_sensors(self):
        self.logger.info("Retrieving sensor list...")

        # read sensor list
        sensors = self.client.query_sensors()

        # gather sensor data
        for s in sensors:
            # parse sensor from SNMP reply
            sensor = SensorInfo(s)
            self.__fetch_sensor(sensor)

    def __fetch_control(self, control):
        self.logger.verbose(
            "Processing control %s.%s %s" % (control.res, control.id, control.desc)
        )

        try:
            # get existing resource
            resource = self.map[control.res]
        except KeyError:
            self.logger.error("Can't get resource name %s" % control.res)
            resource = self.__create_resource(control.res, control.res)

            # create new resource
            resource = ResourceData(control.res, control.res)

            # create resource mapping
            self.map[sensor.res] = resource

        # get control minimum and maximum values
        control.max, control.min = self.client.query_control_limits(
            control.res, control.id
        )

        # dump gathered info
        self.logger.verbose("  Res:  %s" % control.res)
        self.logger.verbose("  Id:   %s" % control.id)
        self.logger.verbose("  Desc: %s" % control.desc)
        self.logger.verbose("  Limits: %s %s" % (control.min, control.max))

        # add to list
        resource.controls += [control]

    def __fetch_controls(self):
        self.logger.info("Retrieving control list...")

        # read control list
        controls = self.client.query_controls()

        # gather control data
        for c in controls:
            control = ControlInfo(c)
            self.__fetch_control(control)

    def fetch(self):
        self.__fetch_sensors()
        self.__fetch_controls()
        return self.map


class MatchInfoItem:
    def __init__(self, matches, sensors, controls):
        self.matches = matches
        self.sensors = sensors
        self.controls = controls

    def __repr__(self):
        return "[\n\t%s\n, \t%s\n, \t%s\n]" % (
            self.matches,
            self.sensors,
            self.controls,
        )

    def match_resource(self, resource):
        for m in self.matches:
            if fnmatch.fnmatch(resource.desc, m[0]) == True:
                return m[1], m[2]
        return None, None

    def match_sensor(self, sensor, default):
        try:
            return self.sensors[sensor.id]
        except KeyError:
            return default

    def match_control(self, control, default):
        try:
            return self.controls[control.id]
        except KeyError:
            return default


class MatchInfo:
    def __init__(self, items):
        self.items = items

    def match_resource(self, resource, resid, defname):
        for item in self.items:
            for m in item.matches:
                id, name = item.match_resource(resource)
                if id:
                    return item, id, name
        return MatchInfoItem([], {}, {}), resid, defname


class TemplateParser:
    def __init__(self, logger):
        self.logger = logger
        self.re_name = re.compile(r'name\s+"(.*)"\s+(\S+)\s+(\S+)')
        self.re_snr = re.compile(r"sensor\s+(\d+)\s+(\S+)")
        self.re_ctl = re.compile(r"control\s+(\d+)\s+(\S+)")

    def parse_file(self, file):
        matches = []
        sensors = {}
        controls = {}

        while True:
            line = file.readline()
            if not line:
                break
            # check for match_name record
            m = self.re_name.match(line)
            if m:
                matches += [(m.group(1), m.group(2), m.group(3))]
                continue
            # check for sensor record
            m = self.re_snr.match(line)
            if m:
                sensors[m.group(1)] = m.group(2)
                continue
            # check for control record
            m = self.re_ctl.match(line)
            if m:
                controls[m.group(1)] = m.group(2)
                continue

        self.logger.debug("    matches %s" % matches)
        self.logger.debug("    sensors %s" % sensors)
        self.logger.debug("    controls %s" % controls)

        return MatchInfoItem(matches, sensors, controls)

    def parse_dir(self, dir):
        parsed_data = []
        with os.scandir(dir) as it:
            self.logger.info("Looking for templates in %s..." % dir)
            for entry in it:
                path = os.path.join(dir, entry.name)
                if entry.is_dir():
                    parsed_data += self.parse_dir(path)
                    continue

                with open(path, "rt") as f:
                    self.logger.verbose("  parsing %s..." % entry.name)
                    parsed_data += [self.parse_file(f)]

        return parsed_data

    def parse(self, dir):
        return MatchInfo(self.parse_dir(dir))


class EpicsDatabaseGenerator:
    # Helper class to write templates and substitution files
    class Writer:
        # Helper to write database records
        class Record:
            def __init__(self, file):
                self.file = file

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                self.file.write("}\n\n")

            def field(self, type, value):
                self.file.write('  field(%s, "%s")\n' % (type, value))

        def __init__(self, path):
            self.path = path

        def __enter__(self):
            self.file = open(self.path, "wt")
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        # write record: use in 'with' statement
        def record(self, type, name):
            self.file.write('record(%s, "%s")\n' % (type, name))
            self.file.write("{\n")
            return self.Record(self.file)

        # write substitution entry
        def sub(self, file, pattern, replacement):
            self.file.write('file "%s" {\n' % file)
            self.file.write("  pattern { %s }\n" % pattern)
            str = None
            for r in replacement:
                if str:
                    str += ', "%s"' % r
                else:
                    str = '  { "%s"' % r
            self.file.write(str + " }\n}\n")

    # Helper class to generate templates
    class TemplateEntry:
        def __init__(self, matches, resource):
            self.matches = matches
            self.resource = resource

        def generate_sensor_record(self, w, sensor):
            name = self.matches.match_sensor(sensor, "SNS-" + sensor.id)
            if sensor.state or sensor.prec >= 1:
                type = "longin"
            else:
                type = "ai"
            with w.record(type, "$(P)%s" % name) as r:
                r.field("DESC", sensor.desc)
                r.field("DTYP", "Snmp")
                if sensor.egu != "unspecified":
                    r.field(" EGU", sensor.egu[:15])
                if sensor.min != "N/A":
                    r.field("LOPR", sensor.min)
                if sensor.lct != "N/A":
                    lolo = sensor.lct
                    low = sensor.lmj
                    losv = "MAJOR"
                else:
                    lolo = sensor.lmj
                    low = sensor.lmn
                    losv = "MINOR"
                if lolo != "N/A":
                    r.field("LOLO", lolo)
                    r.field("LLSV", "MAJOR")
                if low != "N/A" and low != lolo:
                    r.field(" LOW", low)
                    r.field(" LSV", losv)
                if sensor.max != "N/A":
                    r.field("HOPR", sensor.max)
                if sensor.uct != "N/A":
                    hihi = sensor.uct
                    high = sensor.umj
                    hisv = "MAJOR"
                else:
                    hihi = sensor.umj
                    high = sensor.umn
                    hisv = "MINOR"
                if hihi != "N/A":
                    r.field("HIHI", hihi)
                    r.field("HHSV", "MAJOR")
                if high != "N/A" and high != hihi:
                    r.field("HIGH", high)
                    r.field(" HSV", hisv)
                if sensor.state == False and sensor.prec < 1:
                    m = sensor.prec
                    prec = 0
                    while True:
                        m = (m * 10) % 10
                        if not m:
                            break
                        prec = prec + 1
                    r.field("PREC", str(prec))
                if sensor.state:
                    type = "INTEGER: 100"
                else:
                    type = "STRING: 100"
                inp = (
                    "@$(HOST) $(USER_R) SGP-MIB::measurementsExternalSensorValue.$(RESID).%s %s"
                    % (sensor.id, type)
                )
                r.field(" INP", inp)
            return name

        def generate_control_record(self, w, control):
            name = self.matches.match_control(control, "CTL-" + control.id)
            with w.record("longout", "$(P)%s" % name) as r:
                r.field("DESC", control.desc)
                r.field("DTYP", "Snmp")
                if control.min and control.min != "N/A":
                    r.field("LOPR", control.min)
                if control.max and control.max != "N/A":
                    r.field("HOPR", control.max)
                r.field(
                    " OUT",
                    "@$(HOST) $(USER_W) SGP-MIB::ctrlCachedState.$(RESID).%s INTEGER: 100 i"
                    % control.id,
                )
            return name

        def generate_fanout_records(self, w, names, pfx):
            cnt = len(names)
            fans = int((cnt + 14) / 15)
            next = 0
            sfx = ""
            if fans > 1:
                sfx = "1"

            for n in range(fans):
                if n > 0:
                    sfx = str(n + 1)
                with w.record("fanout", "$(P)%s-fanout%s" % (pfx, sfx)) as r:
                    num = cnt
                    if num > 15:
                        num = 15
                    cnt -= num
                    for s in range(num):
                        r.field("LNK%X" % (s + 1), "$(P)" + names[next])
                        next += 1

            if fans > 1:
                with w.record("fanout", "$(P)%s-fanout" % pfx):
                    for s in range(fans):
                        r.field("LNK%X" % (s + 1), "$(P)%s-fanout%X" % (pfx, s + 1))

        def generate(self, w):
            sensors = []
            for s in self.resource.sensors:
                sensors += [self.generate_sensor_record(w, s)]
            controls = []
            for c in self.resource.controls:
                controls += [self.generate_control_record(w, c)]
            if len(self.resource.sensors):
                self.generate_fanout_records(w, sensors, "SNS")
            if len(self.resource.controls):
                self.generate_fanout_records(w, controls, "CTL")
            if len(sensors):
                with w.record("bo", "$(P)UpdateSensors") as r:
                    r.field("DESC", "Update sensors")
                    r.field("PINI", "YES")
                    r.field("SCAN", "10 second")
                    r.field("ZNAM", "Update")
                    r.field("ONAM", "update")
                    r.field("FLNK", "$(P)SNS-fanout")
            if len(controls):
                with w.record("bo", "$(P)UpdateControls") as r:
                    r.field("DESC", "Update controls")
                    r.field("PINI", "YES")
                    r.field("ZNAM", "Update")
                    r.field("ONAM", "update")
                    r.field("FLNK", "$(P)CTL-fanout")

    # Helper class to maintain substitution entries
    class SubstitutionEntry:
        def __init__(self, resid, name):
            self.resid = resid
            self.name = name

    def __init__(self, logger, outdir, prefix, resources, matches):
        self.logger = logger
        self.outdir = outdir
        self.prefix = prefix
        self.resources = resources
        self.matches = matches
        self.templates = {}
        self.substitutions = {}

    def full_name(self, name):
        if self.prefix:
            return self.prefix + "-" + name
        return name

    def full_path(self, name):
        return os.path.join(self.outdir, self.full_name(name))

    def add_template(self, orig_name, matches, resource):
        name = orig_name
        next = 2
        while True:
            try:
                # check if the id slot is busy
                template = self.templates[name]
                # check if the resource is identical
                if template.resource == resource:
                    # return already created template name
                    return name
                # replace template id
                name = orig_name + str(next)
                # increment next
                next = next + 1
            except:
                break
        # create new template
        self.templates[name] = self.TemplateEntry(matches, resource)
        # return template name
        return name

    def add_substitution(self, orig_id, resid, name):
        id = orig_id
        next = 2
        while True:
            try:
                # check if the id slot is busy
                sub = self.substitutions[id]
                # replace id
                id = orig_id + str(next)
                # increment next
                next = next + 1
            except:
                break
        # create new template
        self.substitutions[id] = self.SubstitutionEntry(resid, name)

    def process_resources(self):
        for resid, resource in self.resources.items():
            # find matching name template
            matches, id, name = self.matches.match_resource(
                resource, resid, self.full_name(resid)
            )
            # create and insert a template entry
            name = self.add_template(name, matches, resource)
            # create and insert substitution entry
            self.add_substitution(id, resid, name)

    def generate_info(self):
        with self.Writer(self.full_path("info.template")) as w:
            with w.record("stringin", "$(P)UN") as r:
                r.field("DESC", "Unit Name")
                r.field("DTYP", "Snmp")
                r.field(" INP", "@$(HOST) $(USER_R) SGP-MIB::unitName.0 STRING: 100")
            with w.record("stringin", "$(P)HW") as r:
                r.field("DESC", "HardWare Version")
                r.field("DTYP", "Snmp")
                r.field(
                    " INP", "@$(HOST) $(USER_R) SGP-MIB::hardwareVersion.0 STRING: 100"
                )
            with w.record("stringin", "$(P)FW") as r:
                r.field("DESC", "FirmWare Version")
                r.field("DTYP", "Snmp")
                r.field(
                    " INP", "@$(HOST) $(USER_R) SGP-MIB::firmwareVersion.0 STRING: 100"
                )
            with w.record("stringin", "$(P)MODEL") as r:
                r.field("DESC", "Model Name")
                r.field("DTYP", "Snmp")
                r.field(" INP", "@$(HOST) $(USER_R) SGP-MIB::model.0 STRING: 100")
            with w.record("fanout", "$(P)Info-Fout") as r:
                r.field("LNK1", "$(P)UN")
                r.field("LNK2", "$(P)HW")
                r.field("LNK3", "$(P)FW")
                r.field("LNK4", "$(P)MODEL")
            with w.record("bo", "$(P)UpdateInfo") as r:
                r.field("DESC", "Update setting readbacks")
                r.field("ZNAM", "Revert")
                r.field("ONAM", "revert")
                r.field("FLNK", "$(P)Info-Fout")
                r.field("HIGH", "2")
                r.field(" VAL", "1")
                r.field("PINI", "YES")

    def generate_templates(self):
        # generate resource templates
        self.logger.info("Generating resource templates...")
        # generate info template
        self.generate_info()
        # generate resource templates
        for name, template in self.templates.items():
            path = self.full_path(name + ".template")
            with self.Writer(path) as w:
                self.logger.info("Generating %s..." % path)
                template.generate(w)

    def generate_substituions(self):
        path = os.path.join(self.outdir, self.prefix + ".substitutions")
        # generate substitution
        self.logger.info("Generating %s..." % path)
        with self.Writer(path) as w:
            # info template substitution
            w.sub(self.full_name("info.template"), "P", ["$(PREFIX)"])
            # resource template substitution
            for id, sub in self.substitutions.items():
                name = self.full_name(sub.name + ".template")
                w.sub(name, "P, RESID", ["$(PREFIX)%s:" % id, sub.resid])

    def generate(self):
        self.process_resources()
        self.generate_templates()
        self.generate_substituions()


# parse command line
def parse_command_line():
    parser = argparse.ArgumentParser(
        description="Auto-generate database from a device."
    )
    parser.add_argument("-v", default=None, help="SNMP protocol version")
    parser.add_argument("-c", default=None, help="Community string")
    parser.add_argument(
        "-t", default="name-templates", help="Directory to get name templates from"
    )
    parser.add_argument(
        "-o", default=".", help="Directory to put database templates to"
    )
    parser.add_argument("-p", default="sgp", help="Generated file name prefix")
    parser.add_argument(
        "-d",
        type=int,
        default=1,
        help="Verbosity level: 1 - Info(default), 2 - Verbose, 3 - Debug",
    )
    parser.add_argument(
        "-f", action="store_true", help="Use file backend instead of SNMP access"
    )
    parser.add_argument(
        'source',
        metavar='<target>',
        help="SNMP agent IP address (host name) or file to fetch SNMP data from"
    )
    return parser.parse_args()


def main():
    # parse command line
    args = parse_command_line()

    # create logger
    logger = Logger(args.d)

    # parse name templates
    matches = TemplateParser(logger).parse(args.t)

    # initialize SNMP backend
    if args.f:
        backend = FileBackend(logger, args.source)
    else:
        backend = SnmpBackend(logger, args.source, args.v, args.c)

    # fetch resource information
    resources = ResourceInfoFetcher(logger, backend).fetch()

    # generate database templates
    EpicsDatabaseGenerator(logger, args.o, args.p, resources, matches).generate()
    logger.info("Success")


if __name__ == "__main__":
    main()
