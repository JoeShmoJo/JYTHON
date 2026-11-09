"""
Standalone JSON configuration-package reader.

No selection marker means normal base-only behavior:
    scripts/alt_config/_default.txt + scripts/alt_config/<alternative>.txt

This first version supports scalar/list/dictionary settings only.
CSV table replacement is intentionally deferred to the next increment.
"""

from com.xhaus.jyson import JysonCodec as json
from NWDJyLib.cFile import (
    parallelSafeDigest,
    parallelSafeReadText,
)
import os

MARKER_NAME = 'standalone-override-active.json'
PACKAGE_ROOT = 'scripts/standalone-configurations'

try:
    basestring
except NameError:
    basestring = str


def _read_json(filename, label):
    try:
        text = parallelSafeReadText(filename, 'UTF-8')
        if text.startswith(u'\ufeff'):
            text = text[1:]
        data = json.loads(text)
    except Exception, error:
        raise RuntimeError('Cannot read %s: %s' % (label, error))
    if not isinstance(data, dict):
        raise RuntimeError('%s must contain a JSON object' % label)
    return data


def _active_alternative(network):
    return str(network.getAlternative().getName()).split(':')[-1]


def _find_marker(network):
    output = str(network.getRssRun().getDSSOutputFile())
    output = network.makeAbsolutePathFromWatershed(output)
    directory = os.path.abspath(os.path.dirname(str(output)))

   
    # Match the existing per-output-path behavior used for ensemble members.
    for ignored in range(5):
        marker = os.path.join(directory, MARKER_NAME)
        if os.path.isfile(marker):
            return marker
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    return None


def _package_file(network, selection):
    relative = selection.get('package')
    if not isinstance(relative, basestring) or not relative.strip():
        raise RuntimeError('Standalone override selection requires a package path')

    relative = relative.replace('\\', '/')
    required_prefix = PACKAGE_ROOT + '/'
    if not relative.startswith(required_prefix):
        raise RuntimeError(
            'Standalone override package must be below %s' % PACKAGE_ROOT
        )

    root = os.path.abspath(
        str(network.makeAbsolutePathFromWatershed(PACKAGE_ROOT))
    )
    package = os.path.abspath(
        str(network.makeAbsolutePathFromWatershed(relative))
    )

    if not package.startswith(root + os.sep):
        raise RuntimeError('Invalid standalone override package path')

    if not os.path.isfile(package):
        raise RuntimeError('Standalone override package is missing: ' + package)

    return package


def package_overrides(network):
    """
    Return selected package settings for Alternative_Setup.

    No marker returns an empty dictionary, preserving normal standalone behavior.
    """
    marker = _find_marker(network)
    if marker is None:
        return {}

    selection = _read_json(marker, 'standalone override selection')
    if selection.get('schema_version') != 1:
        raise RuntimeError('Unsupported standalone override selection schema')
    if selection.get('kind') != 'standalone-override-selection':
        raise RuntimeError('Invalid standalone override selection kind')

    alternative = _active_alternative(network)
    if selection.get('model_alternative') != alternative:
        raise RuntimeError(
            'Standalone override alternative does not match active alternative: ' +
            alternative
        )

    package_file = _package_file(network, selection)
    package = _read_json(package_file, 'standalone configuration package')

    if package.get('schema_version') != 1:
        raise RuntimeError('Unsupported standalone configuration package schema')
    if package.get('kind') != 'standalone-configuration':
        raise RuntimeError('Invalid standalone configuration package kind')
    if package.get('mode') not in ('patch', 'snapshot'):
        raise RuntimeError('Standalone configuration mode must be patch or snapshot')
    if package.get('model_alternative') != alternative:
        raise RuntimeError(
            'Standalone configuration package does not match active alternative: ' +
            alternative
        )

    settings = package.get('settings', {})
    if not isinstance(settings, dict):
        raise RuntimeError('Standalone configuration settings must be an object')

    tables = package.get('tables', {})
    if not isinstance(tables, dict):
        raise RuntimeError('Standalone configuration tables must be an object')

    result = dict(settings)

    if tables:
        package_relative = selection['package'].replace('\\', '/')
        package_folder = package_relative.rsplit('/', 1)[0]

        for key, relative in tables.items():
            if not isinstance(key, basestring) or not key.strip():
                raise RuntimeError('Standalone configuration table key is invalid')
            if key in result:
                raise RuntimeError(
                    'Standalone configuration key appears in both settings and tables: ' +
                    key
                )
            if not isinstance(relative, basestring) or not relative.strip():
                raise RuntimeError(
                    'Standalone configuration table path is invalid for: ' + key
                )

            relative = relative.replace('\\', '/')
            if (os.path.isabs(relative) or relative.startswith('/') or
                    '..' in relative.split('/')):
                raise RuntimeError(
                    'Standalone configuration table path must stay within package: ' +
                    key
                )

            watershed_relative = package_folder + '/' + relative
            full_path = str(
                network.makeAbsolutePathFromWatershed(watershed_relative)
            )
            if not os.path.isfile(full_path):
                raise RuntimeError(
                    'Standalone configuration table is missing for %s: %s' %
                    (key, watershed_relative)
                )

            # Keep this watershed-relative because existing rule modules call
            # network.makeAbsolutePathFromWatershed on Alternative_Setup values.
            result[key] = watershed_relative
    if package['mode'] == 'snapshot':
        manifest_file = os.path.join(
            os.path.dirname(package_file),
            'manifest.json'
        )
        if not os.path.isfile(manifest_file):
            raise RuntimeError(
                'Snapshot package manifest is missing: ' + manifest_file
            )

        manifest = _read_json(manifest_file, 'standalone snapshot manifest')
        if manifest.get('schema_version') != 1:
            raise RuntimeError('Unsupported standalone snapshot manifest schema')
        if manifest.get('kind') != 'standalone-configuration-manifest':
            raise RuntimeError('Invalid standalone snapshot manifest kind')
        if manifest.get('mode') != 'snapshot':
            raise RuntimeError('Standalone snapshot manifest mode must be snapshot')
        if manifest.get('model_alternative') != alternative:
            raise RuntimeError(
                'Standalone snapshot manifest does not match active alternative: ' +
                alternative
            )

        expected_config_hash = manifest.get('configuration_sha256')
        actual_config_hash = parallelSafeDigest(package_file)
        if (not isinstance(expected_config_hash, basestring) or
                expected_config_hash.lower() != actual_config_hash.lower()):
            raise RuntimeError(
                'Standalone snapshot configuration checksum mismatch'
            )

        expected_tables = manifest.get('table_sha256')
        if not isinstance(expected_tables, dict):
            raise RuntimeError(
                'Standalone snapshot manifest table hashes must be an object'
            )

        configured_tables = sorted(tables.values())
        manifest_tables = sorted(expected_tables.keys())
        if configured_tables != manifest_tables:
            raise RuntimeError(
                'Standalone snapshot manifest table list does not match configuration'
            )

        for relative in configured_tables:
            table_file = os.path.abspath(
                os.path.join(
                    os.path.dirname(package_file),
                    relative.replace('/', os.sep)
                )
            )
            actual_hash = parallelSafeDigest(table_file)
            expected_hash = expected_tables[relative]
            if (not isinstance(expected_hash, basestring) or
                    expected_hash.lower() != actual_hash.lower()):
                raise RuntimeError(
                    'Standalone snapshot table checksum mismatch: ' + relative
                )
    result['standaloneConfigurationName'] = str(
        package.get('name', os.path.basename(package_file))
    )
    result['standaloneConfigurationMode'] = package['mode']

    if tables:
        network.printMessage(
            'Standalone configuration tables: ' + ', '.join(sorted(tables.keys()))
        )
    network.printMessage(
        'Standalone configuration package: %s [%s]' %
        (result['standaloneConfigurationName'], package['mode'])
    )
    return result