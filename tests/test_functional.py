import os
import unittest
import sys
import tempfile

import requests

from kinto_wizard.__main__ import main


class RoundTrip(unittest.TestCase):
    def setUp(self):
        self.server = os.getenv("SERVER_URL", "http://localhost:8888/v1")
        self.auth = os.getenv("AUTH", "user:pass")
        self.file = os.getenv("FILE", "tests/kinto.yaml")
        requests.post(self.server + "/__flush__")

    def test_round_trip(self):
        cmd = 'kinto-wizard {} --server={} --auth={}'
        load_cmd = cmd.format("load {}".format(self.file),
                              self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()

        load_cmd = cmd.format("dump", self.server, self.auth)

        with tempfile.NamedTemporaryFile() as fp:
            sys.argv = load_cmd.split(" ")
            stdout = sys.stdout
            sys.stdout = fp
            main()
            fp.flush()
            sys.stdout = stdout

            # Check that identical to original file.
            original = open(self.file).read()
            generated = open(fp.name).read()
            assert original == generated
