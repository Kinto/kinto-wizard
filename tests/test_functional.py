import builtins
import io
import os
import pytest
import unittest
import sys
from contextlib import contextmanager, redirect_stdout

import requests

from kinto_http import Client, exceptions
from kinto_wizard.__main__ import main


class DryRunLoad(unittest.TestCase):
    def setUp(self):
        self.server = os.getenv("SERVER_URL", "http://localhost:8888/v1")
        self.auth = os.getenv("AUTH", "user:pass")
        self.file = os.getenv("FILE", "tests/kinto.yaml")
        requests.post(self.server + "/__flush__")

    def test_dry_round_trip(self):
        cmd = 'kinto-wizard {} --server={} --auth={} --dry-run'
        load_cmd = cmd.format("load {}".format(self.file),
                              self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()
        client = Client(server_url=self.server, auth=tuple(self.auth.split(':')))
        with pytest.raises(exceptions.KintoException):
            client.get_bucket(id="staging")


@contextmanager
def mockInput(mock):
    original_input = builtins.input
    builtins.input = lambda _: mock
    yield
    builtins.input = original_input


class SimpleDump(unittest.TestCase):
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

        dump_cmd = cmd.format("dump", self.server, self.auth)
        sys.argv = dump_cmd.split(" ")
        output = io.StringIO()
        with redirect_stdout(output):
            main()
        output.flush()

        # Check that identical to original file.
        generated = output.getvalue()
        with open(self.file) as f:
            assert f.read() == generated


class FullDump(unittest.TestCase):
    def setUp(self):
        self.server = os.getenv("SERVER_URL", "http://localhost:8888/v1")
        self.auth = os.getenv("AUTH", "user:pass")
        self.file = os.getenv("FILE", "tests/kinto-full.yaml")
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
        with open(self.file) as f:
            assert f.read() == generated

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

    def test_round_trip_with_client_wins_and_delete_missing_records(self):
        # Load some data
        cmd = 'kinto-wizard {} --server={} --auth={}'
        load_cmd = cmd.format("load {}".format(self.file),
                              self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()

        # Change something that could make the server to fail.
        client = Client(server_url=self.server, auth=tuple(self.auth.split(':')))
        client.create_record(bucket='build-hub', collection='archives',
                             id='8031d549-0a69-48dd-b240-feef94688d47', data={})
        cmd = 'kinto-wizard {} --server={} -D --auth={} --force --delete-records'
        load_cmd = cmd.format("load {}".format(self.file),
                              self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()
        with pytest.raises(exceptions.KintoException) as exc:
            client.get_record(bucket='build-hub', collection='archives',
                              id='8031d549-0a69-48dd-b240-feef94688d47')
        assert "'Not Found'" in str(exc.value)

    def test_round_trip_with_delete_missing_records_ask_for_confirmation(self):
        # Load some data
        cmd = 'kinto-wizard {} --server={} --auth={}'
        load_cmd = cmd.format("load {}".format(self.file),
                              self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()

        # Change something that could make the server to fail.
        client = Client(server_url=self.server, auth=tuple(self.auth.split(':')))
        client.create_record(bucket='build-hub', collection='archives',
                             id='8031d549-0a69-48dd-b240-feef94688d47', data={})
        cmd = 'kinto-wizard {} --server={} -D --auth={} --delete-records'
        load_cmd = cmd.format("load {}".format(self.file),
                              self.server, self.auth)
        sys.argv = load_cmd.split(" ")

        with mockInput('yes'):
            main()

        with pytest.raises(exceptions.KintoException) as exc:
            client.get_record(bucket='build-hub', collection='archives',
                              id='8031d549-0a69-48dd-b240-feef94688d47')
        assert "'Not Found'" in str(exc.value)

    def test_round_trip_with_delete_missing_records_handle_misconfirmation(self):
        # Load some data
        cmd = 'kinto-wizard {} --server={} --auth={}'
        load_cmd = cmd.format("load {}".format(self.file),
                              self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()

        # Change something that could make the server to fail.
        client = Client(server_url=self.server, auth=tuple(self.auth.split(':')))
        client.create_record(bucket='build-hub', collection='archives',
                             id='8031d549-0a69-48dd-b240-feef94688d47', data={})
        cmd = 'kinto-wizard {} --server={} -D --auth={} --delete-records'
        load_cmd = cmd.format("load {}".format(self.file),
                              self.server, self.auth)
        sys.argv = load_cmd.split(" ")

        with mockInput('no'):
            with pytest.raises(SystemExit):
                main()


class DataRecordsDump(unittest.TestCase):
    def setUp(self):
        self.server = os.getenv("SERVER_URL", "http://localhost:8888/v1")
        self.auth = os.getenv("AUTH", "user:pass")
        self.file = os.getenv("FILE", "tests/kinto-full.yaml")
        requests.post(self.server + "/__flush__")

    def test_round_trip(self):
        # Load some data
        cmd = 'kinto-wizard {} --server={} --auth={}'
        load_cmd = cmd.format("load {}".format(self.file),
                              self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()

        cmd = 'kinto-wizard {} --server={} --auth={} --data --records'
        load_cmd = cmd.format("dump", self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        output = io.StringIO()
        with redirect_stdout(output):
            main()
        output.flush()

        # Check that identical to original file.
        generated = output.getvalue()
        with open(self.file) as f:
            assert f.read() == generated


class BucketCollectionSelectionableDump(unittest.TestCase):
    def setUp(self):
        self.server = os.getenv("SERVER_URL", "http://localhost:8888/v1")
        self.auth = os.getenv("AUTH", "user:pass")
        self.file = os.getenv("FILE", "tests/dumps/dump-full.yaml")
        requests.post(self.server + "/__flush__")

    def load(self, bucket=None, collection=None):
        cmd = 'kinto-wizard {} --server={} --auth={}'

        if bucket:
            cmd += ' --bucket={}'.format(bucket)

        if collection:
            cmd += ' --collection={}'.format(collection)

        load_cmd = cmd.format("load {}".format(self.file),
                              self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()

    def dump(self, bucket=None, collection=None):
        cmd = 'kinto-wizard {} --server={} --auth={}'
        dump_cmd = cmd.format("dump --full", self.server, self.auth)

        if bucket:
            dump_cmd += ' --bucket={}'.format(bucket)

        if collection:
            dump_cmd += ' --collection={}'.format(collection)

        sys.argv = dump_cmd.split(" ")
        output = io.StringIO()
        with redirect_stdout(output):
            main()
        output.flush()

        # Check that identical to original file.
        return output.getvalue()

    def test_round_trip_with_bucket_selection_on_load(self):
        self.load(bucket="natim")
        generated = self.dump()
        with open("tests/dumps/dump-natim.yaml") as f:
            assert f.read() == generated

    def test_round_trip_with_bucket_selection(self):
        self.load()
        generated = self.dump(bucket="natim")
        with open("tests/dumps/dump-natim.yaml") as f:
            assert f.read() == generated

    def test_round_trip_with_bucket_collection_selection_on_load(self):
        self.load(bucket="natim", collection="toto")
        generated = self.dump()
        with open("tests/dumps/dump-natim-toto-groups.yaml") as f:
            assert f.read() == generated

    def test_round_trip_with_bucket_collection_selection(self):
        self.load()
        generated = self.dump(bucket="natim", collection="toto")
        with open("tests/dumps/dump-natim-toto.yaml") as f:
            assert f.read() == generated

    def test_round_trip_with_collection_selection_on_load(self):
        self.load(collection="toto")
        generated = self.dump()
        with open("tests/dumps/dump-toto-groups.yaml") as f:
            assert f.read() == generated

    def test_round_trip_with_collection_selection(self):
        self.load()
        generated = self.dump(collection="toto")
        with open("tests/dumps/dump-toto.yaml") as f:
            assert f.read() == generated
