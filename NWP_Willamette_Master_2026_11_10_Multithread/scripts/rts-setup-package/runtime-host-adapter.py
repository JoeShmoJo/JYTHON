# Runtime dispatch for existing native rule wrappers; no GUI or source mutation.
_standalone_initialize_rule = initialize_rule
_standalone_alternative_overrides = alternative_overrides


def _rts_compute(network):
    try:
        if network.getStateVariable('Alternative_Setup').varGet('cwmsCompute'):
            return True
    except Exception:
        pass
    # Before Alternative_Setup initialization, an applied RTS marker is scoped
    # to the actual output file, never the selected GUI forecast or mode JSON.
    directory = os.path.dirname(str(network.makeAbsolutePathFromWatershed(
        str(network.getRssRun().getDSSOutputFile()))))
    for ignored in range(5):
        if os.path.isfile(os.path.join(directory,'rts-baseline-config-active.json')):
            return True
        parent = os.path.dirname(directory)
        if parent==directory:break
        directory=parent
    return False


def initialize_rule(module_name, rule, network, namespace=None):
    if module_name in RULE_KEYS and _rts_compute(network):
        from rts_baseline_runtime import initialize_rule as rts_initialize
        return rts_initialize(module_name,rule,network,namespace)
    return _standalone_initialize_rule(module_name,rule,network,namespace)


def alternative_overrides(network):
    if _rts_compute(network):
        from rts_baseline_runtime import alternative_overrides as rts_overrides
        return rts_overrides(network)
    return _standalone_alternative_overrides(network)
