"""Build installer TLS trust using explicit configuration or Windows trusted roots."""
import argparse
import os
from pathlib import Path
import ssl
import urllib.request

SERVER_AUTH = '1.3.6.1.5.5.7.3.1'


def configure(output):
    for name in ('PIP_CERT', 'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE', 'SSL_CERT_FILE'):
        configured = os.environ.get(name)
        if configured:
            path = Path(configured).resolve()
            if not path.is_file():
                raise FileNotFoundError('Configured CA bundle does not exist: ' + str(path))
            ssl.create_default_context(cafile=str(path))
            return path
    if not hasattr(ssl, 'enum_certificates'):
        raise RuntimeError('Windows certificate store is unavailable; supply an approved CA bundle.')
    import certifi
    certificates = []
    for certificate, encoding, trust in ssl.enum_certificates('ROOT'):
        if encoding == 'x509_asn' and (trust is True or SERVER_AUTH in trust):
            certificates.append(ssl.DER_cert_to_PEM_cert(certificate).encode('ascii'))
    content = Path(certifi.where()).read_bytes() + b'\n' + b'\n'.join(certificates)
    output = Path(output).resolve()
    output.write_bytes(content)
    ssl.create_default_context(cafile=str(output))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    bundle = configure(args.output)
    # Fail once with the real certificate error before pip starts its retry loop.
    context = ssl.create_default_context(cafile=str(bundle))
    with urllib.request.urlopen('https://pypi.org/pypi/altgraph/json', context=context, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError('PyPI TLS preflight failed: HTTP ' + str(response.status))
    print(str(bundle), flush=True)


if __name__ == '__main__':
    main()
