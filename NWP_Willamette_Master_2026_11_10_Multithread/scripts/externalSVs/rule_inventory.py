"""Document configured rules without evaluating them or opening DSS."""
from java.lang import Boolean, Class, Number, String
from java.lang import Exception as JavaException
from java.lang.reflect import Modifier
from hec.model import PairedValues, PairedValuesExt, SeasonalPairedValues, SeasonalRecord
from hec.rss.model import ConstantRelease, ReleaseFuncOpRule, ScriptOpRule


def recordUnits(target, key, getter):
    try:
        target[key] = str(getter())
    except (Exception, JavaException) as error:
        target[key] = None
        target.setdefault("unit_errors", {})[key] = str(error)


def fieldValue(value):
    if isinstance(value, float) and (value != value or abs(value) == float('inf')):
        return str(value)
    if value is None or isinstance(value, (bool, basestring, int, long, float)):
        return value
    if isinstance(value, Boolean):
        return bool(value.booleanValue())
    if isinstance(value, String):
        return unicode(value)
    if isinstance(value, Number):
        return fieldValue(float(value.doubleValue()))
    if isinstance(value, SeasonalRecord):
        times = list(value.getTimeArray() or [])
        record = {"times": times, "values": [fieldValue(value.getValue(i)) for i in range(len(times))],
                  "interpolation": value.getInterpolationType()}
        recordUnits(record, "units", value.getUnitsString)
        return record
    if isinstance(value, (PairedValues, PairedValuesExt)):
        table = {"interpolation": value.getInterpolationType()}
        recordUnits(table, "x_units", value.getParamXUnitsString)
        recordUnits(table, "y_units", value.getParamYUnitsString)
        if isinstance(value, PairedValuesExt):
            table["points"] = [[fieldValue(p.xval), [fieldValue(y) for y in p.yval]]
                               for p in value.getDataVector()]
        else:
            table["points"] = [list(pair) for pair in zip(
                map(fieldValue, value.getXArray()), map(fieldValue, value.getYArray()))]
        if isinstance(value, SeasonalPairedValues):
            table["curve_times"] = list(value.getTimeArray() or [])
            table["time_interpolation"] = value.getTimeInterpolationType()
        return table
    if hasattr(value, 'getClass') and Class.isArray(value.getClass()):
        return [fieldValue(item) for item in value]
    # Jython also exposes primitive Java arrays as array.array-compatible objects.
    if hasattr(value, 'typecode') and hasattr(value, 'tolist'):
        return [fieldValue(item) for item in value.tolist()]
    raise ValueError("Structured field requires a dedicated exporter")


def ruleSettings(rule):
    fields, omitted = {}, {}
    cls = rule.getClass()
    # Jython can resolve cls.getName to an instance method of the represented class.
    while cls is not None and Class.getName(cls).startswith('hec.rss.model.'):
        for field in Class.getDeclaredFields(cls):
            if Modifier.isStatic(field.getModifiers()) or field.isSynthetic():
                continue
            name = str(Class.getSimpleName(cls)) + "." + str(field.getName())
            try:
                fields[name] = fieldValue(rule.getFieldObject(field))
            except (Exception, JavaException) as error:
                omitted[name] = str(error)
        cls = Class.getSuperclass(cls)
    return fields, omitted


def buildRuleInventory(opSet, releaseReport):
    definitions, memberships = {}, {}

    def register(rule, ruleIndex=None):
        name = str(rule)
        controller = str(rule.getController())
        key = "%s / %s" % (controller, name)
        if ruleIndex is None:
            ruleIndex = rule.getIndex()
        if key in definitions and not rule.equals(definitions[key][0]):
            key += " [%s]" % ruleIndex
        if key not in definitions:
            fields, omitted = ruleSettings(rule)
            entry = {"name": name, "controller": controller, "class": str(Class.getName(rule.getClass())),
                     "description": rule.getDescription(), "rule_index": ruleIndex,
                     "fields": fields, "omitted_fields": omitted,
                     "daily_values": "native_output_required"}
            if isinstance(rule, ScriptOpRule):
                entry["script"] = {"text": rule.getScriptText(), "uses_java_class": rule.useJavaClass(),
                                   "java_class_path": rule.getJavaClassPath()}
            if isinstance(rule, (ConstantRelease, ReleaseFuncOpRule)):
                try:
                    entry["release_definition"] = releaseReport(rule)
                    entry["daily_values"] = "reconstruction_candidate"
                except (Exception, JavaException) as error:
                    entry["release_definition_error"] = str(error)
            definitions[key] = (rule, entry)
        return key

    for zoneId in opSet.getZoneVector():
        zone = opSet.getZone(str(zoneId))
        references = []
        for ref in zone.getRuleRefs([]):
            item = {"name": str(ref.getName()), "priority": float(ref.getPriority()),
                    "controller_index": ref.getOpControllerIndex(), "rule_index": ref.getRuleIndex()}
            try:
                item["rule"] = register(ref.getRule(), item["rule_index"])
            except (Exception, JavaException) as error:
                item["unavailable"] = str(error)
            references.append(item)
        memberships[str(zone)] = references

    unlisted = []
    for rule in opSet.getRules([]):
        try:
            register(rule)
        except (Exception, JavaException) as error:
            unlisted.append({"name": str(rule), "unavailable": str(error)})
    return {"definitions": dict((key, value[1]) for key, value in definitions.items()),
            "zone_references": memberships, "unavailable": unlisted}
