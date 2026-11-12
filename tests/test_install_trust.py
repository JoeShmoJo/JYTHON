import contextlib
import importlib.util
import io
import os
from pathlib import Path
import ssl
import sys
import tempfile
import unittest
from unittest.mock import patch

SETUP=Path(__file__).resolve().parents[1]/'NWP_Willamette_Master_2026_11_10_Multithread/scripts/ExternalPython/PythonSetup1stTime'
spec=importlib.util.spec_from_file_location('install_trust',SETUP/'configure_install_trust.py')
trust=importlib.util.module_from_spec(spec);spec.loader.exec_module(trust)

class InstallTrustTests(unittest.TestCase):
    def test_explicit_bundle_is_preserved_and_missing_bundle_fails(self):
        import certifi
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'PIP_CERT':certifi.where()},clear=True):
            output=Path(temp)/'generated.pem'
            self.assertEqual(trust.configure(output),Path(certifi.where()).resolve())
            self.assertFalse(output.exists())
            os.environ['PIP_CERT']=str(Path(temp)/'missing.pem')
            with self.assertRaises(FileNotFoundError):trust.configure(output)

    def test_only_windows_roots_trusted_for_server_auth_are_added(self):
        import certifi
        certificate=ssl.create_default_context(cafile=certifi.where()).get_ca_certs(binary_form=True)[0]
        roots=[(certificate,'x509_asn',True),(certificate,'x509_asn',{'wrong-purpose'}),
               (certificate,'pkcs_7_asn',True)]
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{},clear=True),patch.object(ssl,'enum_certificates',return_value=roots,create=True):
            output=Path(temp)/'generated.pem'
            self.assertEqual(trust.configure(output),output)
            expected=Path(certifi.where()).read_bytes()+b'\n'+ssl.DER_cert_to_PEM_cert(certificate).encode('ascii')
            self.assertEqual(output.read_bytes(),expected)
            ssl.create_default_context(cafile=str(output))

    def test_tls_preflight_failure_is_not_bypassed(self):
        import certifi
        with patch.dict(os.environ,{'PIP_CERT':certifi.where()},clear=True),patch.object(sys,'argv',['trust','--output','unused.pem']),patch.object(trust.urllib.request,'urlopen',side_effect=ssl.SSLCertVerificationError('untrusted chain')) as request:
            with self.assertRaises(ssl.SSLCertVerificationError):trust.main()
            self.assertIsInstance(request.call_args.kwargs['context'],ssl.SSLContext)
            self.assertEqual(request.call_args.kwargs['context'].verify_mode,ssl.CERT_REQUIRED)

if __name__=='__main__':unittest.main()
