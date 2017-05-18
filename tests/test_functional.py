import io
import os
import unittest
import sys
try:
    # Python 3
    from contextlib import redirect_stdout
except ImportError:
    # Python 2
    from contextlib import contextmanager

    @contextmanager
    def redirect_stdout(filehandler):
        stdout = sys.stdout
        sys.stdout = filehandler
        yield
        filehandler.flush()
        sys.stdout = stdout  # restore stdout

import requests

from kinto_wizard.__main__ import main


class SimpleDump(unittest.TestCase):
    def setUp(self):
        self.server = os.getenv("SERVER_URL", "http://localhost:8888/v1")
        self.auth = os.getenv("AUTH", "user:pass")
        self.file = os.getenv("FILE", "tests/kinto.yaml")
        self.original = open(self.file).read()
        requests.post(self.server + "/__flush__")

    def test_round_trip(self):
        cmd = 'kinto-wizard {} --server={} --auth={}'
        load_cmd = cmd.format("load {}".format(self.file),
                              self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()

        dump_cmd = cmd.format("dump", self.server, self.auth)
        sys.argv = dump_cmd.split(" ")
        output = io.StringIO()
        with redirect_stdout(output):
            main()
        output.flush()

        # Check that identical to original file.
        generated = output.getvalue()
        assert self.original == generated


class FullDump(unittest.TestCase):
    def setUp(self):
        self.server = os.getenv("SERVER_URL", "http://localhost:8888/v1")
        self.auth = os.getenv("AUTH", "user:pass")
        self.file = os.getenv("FILE", "tests/kinto-full.yaml")
        self.original = open(self.file).read()
        requests.post(self.server + "/__flush__")

    def test_round_trip(self):
        # Load some data
        cmd = 'kinto-wizard {} --server={} --auth={}'
        load_cmd = cmd.format("load {}".format(self.file),
                              self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()

        cmd = 'kinto-wizard {} --server={} --auth={} --full'
        load_cmd = cmd.format("dump", self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        output = io.StringIO()
        with redirect_stdout(output):
            main()
        output.flush()

        # Check that identical to original file.
        generated = output.getvalue()
        assert self.original == generated
