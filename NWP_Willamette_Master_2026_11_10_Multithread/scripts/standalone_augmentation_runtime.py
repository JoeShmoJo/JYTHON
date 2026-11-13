"""Jython-compatible, simulation-scoped configuration for external augmentation."""
import json
import os
import re


def configuration_path(output_file, fpart, read_text, digest):
    directory = os.path.abspath(os.path.dirname(str(output_file)))
    for ignored in range(5):
        marker = os.path.join(directory, 'standalone-augmentation-active.json')
        if os.path.isfile(marker):
            active = json.loads(read_text(marker))
            baseline = str(active['baseline_run_code']).upper()
            match = re.match(r'^C:([0-9]+)\|(.+)$', str(fpart).upper())
            code = match.group(2) if match else str(fpart).upper()
            # Other alternatives in the same simulation retain their own inputs.
            if code[:-1] != baseline[:-1]:
                return None
            if (not code[-1:].isdigit() or not baseline.endswith('0')
                    or active.get('status') != 'loaded-awaiting-native-compute'):
                raise AssertionError('Standalone augmentation has an invalid active scheme')
            if active['run_type'] == 'ensemble':
                if match is None or int(match.group(1)) not in active['members']:
                    raise AssertionError('Standalone augmentation does not cover this member')
            elif match is not None:
                raise AssertionError('Standalone POR augmentation cannot be used for ensemble compute')
            path = os.path.abspath(os.path.join(directory, active['configuration_csv']))
            if not path.startswith(directory + os.sep):
                raise AssertionError('Standalone augmentation configuration is outside its simulation')
            expected = active['configuration_sha256']['MinFlowSalemAlbanyConfig.csv']
            if digest(path) != expected:
                raise AssertionError('Standalone augmentation configuration checksum mismatch')
            return path
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    return None


def for_compute(network, alternative):
    from NWDJyLib.cFile import parallelSafeReadText, parallelSafeDigest
    output = str(alternative.varGet('fileNameSimulation'))
    output = network.makeAbsolutePathFromWatershed(output)
    return configuration_path(output, alternative.varGet('dssOutputFpart'),
                              lambda path: parallelSafeReadText(path, 'UTF-8'),
                              parallelSafeDigest)


def external_trial_configuration(network, alternative):
    # Trial zero retains its configured baseline behavior. Explicitly loaded
    # two-step releases apply to the selected alternative's augmented trials.
    fpart = str(alternative.varGet('dssOutputFpart'))
    if not fpart[-1:].isdigit() or fpart.endswith('0'):
        return None
    return for_compute(network, alternative)
