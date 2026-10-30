import os
import ssl
import sys
import tarfile
import tempfile
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agyauto import cli  # noqa: E402


def _tarball():
    d = tempfile.mkdtemp()
    root = os.path.join(d, "agyauto-main")
    os.makedirs(root)
    with open(os.path.join(root, "VERSION"), "w") as f:
        f.write("9.9.9\n")
    path = os.path.join(d, "src.tgz")
    with tarfile.open(path, "w:gz") as tf:
        tf.add(root, arcname="agyauto-main")
    return path


class Download(unittest.TestCase):
    def test_falls_back_to_curl_on_certificate_error(self):
        url = "file://" + _tarball()
        err = urllib.error.URLError(ssl.SSLCertVerificationError("unable to get local issuer certificate"))
        with mock.patch("urllib.request.urlopen", side_effect=err), mock.patch.dict(os.environ, {"AGYAUTO_TARBALL": url}):
            tmp, src = cli._fetch_latest()
        self.assertTrue(os.path.exists(os.path.join(src, "VERSION")))

    def test_other_network_errors_are_not_masked(self):
        err = urllib.error.URLError(OSError("network unreachable"))
        with mock.patch("urllib.request.urlopen", side_effect=err), self.assertRaises(urllib.error.URLError):
            cli._download("https://example.invalid/x", os.path.join(tempfile.mkdtemp(), "x"))


if __name__ == "__main__":
    unittest.main()
