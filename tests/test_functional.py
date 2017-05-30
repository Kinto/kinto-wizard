import io
import os
import unittest
import sys
from contextlib import redirect_stdout

import requests

from kinto_http import Client
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

    def test_round_trip_with_client_wins(self):
        # Load some data
        cmd = 'kinto-wizard {} --server={} --auth={}'
        load_cmd = cmd.format("load {}".format(self.file),
                              self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()

        # Change something that could make the server to fail.
        client = Client(server_url=self.server, auth=tuple(self.auth.split(':')))
        client.update_record(bucket='build-hub', collection='archives',
                             id='0831d549-0a69-48dd-b240-feef94688d47', data={})
        record = client.get_record(bucket='build-hub', collection='archives',
                                   id='0831d549-0a69-48dd-b240-feef94688d47')
        assert set(record['data'].keys()) == {'id', 'last_modified'}
        cmd = 'kinto-wizard {} --server={} -D --auth={} --force'
        load_cmd = cmd.format("load {}".format(self.file),
                              self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()
        record = client.get_record(bucket='build-hub', collection='archives',
                                   id='0831d549-0a69-48dd-b240-feef94688d47')
        assert set(record['data'].keys()) != {'id', 'last_modified'}
