import os
import unittest
import subprocess
import tempfile

import requests


class RoundTrip(unittest.TestCase):
    def setUp(self):
        self.server = os.getenv("SERVER_URL", "http://localhost:8888")
        self.auth = os.getenv("AUTH", "user:pass")
        self.file = os.getenv("FILE", "tests/kinto.yml")
        requests.post(self.server + "/__flush__")

    def test_round_trip(self):
        cmd = 'kinto-wizard {} --server="{}" --auth="{}"'

        load_cmd = cmd.format("load {}".format(self.file),
                              self.server, self.auth)
        subprocess.check_call(load_cmd.split(" "))

        load_cmd = cmd.format("dump", self.server, self.auth)

        with tempfile.NameTemporaryFile() as fp:
            subprocess.check_call(load_cmd.split(" "), stdout=fp)
            diff_cmd = 'diff {} {}'.format(self.file, fp.name)
            subprocess.check_call(diff_cmd.split(" "))
