import builtins
import io
import os
import sys
import unittest
from contextlib import contextmanager, redirect_stdout

import pytest
import requests
from kinto_http import Client, exceptions
from kinto_wizard.__main__ import main
from ruamel.yaml import YAML


def load(server, auth, file, bucket=None, collection=None, extra=None):
    cmd = "kinto-wizard {} --server={} --auth={}"

    if bucket:
        cmd += " --bucket={}".format(bucket)

    if collection:
        cmd += " --collection={}".format(collection)

    if extra:
        cmd += " " + extra

    load_cmd = cmd.format("load {}".format(file), server, auth)
    sys.argv = load_cmd.strip().split(" ")
    return main()


def dump(server, auth, bucket=None, collection=None):
    cmd = "kinto-wizard {} --server={} --auth={}"
    dump_cmd = cmd.format("dump --full", server, auth)

    if bucket:
        dump_cmd += " --bucket={}".format(bucket)

    if collection:
        dump_cmd += " --collection={}".format(collection)

    sys.argv = dump_cmd.split(" ")
    output = io.StringIO()
    with redirect_stdout(output):
        main()
    output.flush()

    # Check that identical to original file.
    return output.getvalue()


def validate(filename):
    sys.argv = ["kinto-wizard", "validate", filename]
    return main()


def assert_identical(a, b):
    yaml = YAML(typ="safe")
    a_parsed = yaml.load(a)
    b_parsed = yaml.load(b)
    assert a_parsed == b_parsed


class FunctionalTest(unittest.TestCase):
    server = os.getenv("SERVER_URL", "http://localhost:8888/v1")
    auth = os.getenv("AUTH", "user:pass")
    file = os.getenv("FILE", "tests/kinto.yaml")

    def setUp(self):
        requests.post(self.server + "/__flush__")

    def load(self, bucket=None, collection=None, filename=None, extra=None):
        return load(self.server, self.auth, filename or self.file, bucket, collection, extra)

    def dump(self, bucket=None, collection=None):
        return dump(self.server, self.auth, bucket, collection)

    def validate(self, filename=None, code=0):
        try:
            validate(filename or self.file)
        except SystemExit as e:
            if e.code == code:
                return
            else:
                self.fail(f"Unexpected validation status {e.code} != {code}")


class DryRunLoad(FunctionalTest):
    def test_dry_round_trip(self):
        cmd = "kinto-wizard {} --server={} --auth={} --dry-run"
        load_cmd = cmd.format("load {}".format(self.file), self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()
        client = Client(server_url=self.server, auth=tuple(self.auth.split(":")))
        with pytest.raises(exceptions.KintoException):
            client.get_bucket(id="staging")


@contextmanager
def mockInput(mock):
    original_input = builtins.input
    builtins.input = lambda _: mock
    yield
    builtins.input = original_input


class SimpleDump(FunctionalTest):
    def test_round_trip(self):
        cmd = "kinto-wizard {} --server={} --auth={}"
        load_cmd = cmd.format("load {}".format(self.file), self.server, self.auth)
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
            assert_identical(f.read(), generated)


class FullDump(FunctionalTest):
    file = os.getenv("FILE", "tests/kinto-full.yaml")

    def test_round_trip(self):
        # Load some data
        cmd = "kinto-wizard {} --server={} --auth={}"
        load_cmd = cmd.format("load {}".format(self.file), self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()

        cmd = "kinto-wizard {} --server={} --auth={} --full"
        load_cmd = cmd.format("dump", self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        output = io.StringIO()
        with redirect_stdout(output):
            main()
        output.flush()

        # Check that identical to original file.
        generated = output.getvalue()
        with open(self.file) as f:
            assert_identical(f.read(), generated)

    def test_round_trip_with_client_wins(self):
        # Load some data
        cmd = "kinto-wizard {} --server={} --auth={}"
        load_cmd = cmd.format("load {}".format(self.file), self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()

        # Change something that could make the server to fail.
        client = Client(server_url=self.server, auth=tuple(self.auth.split(":")))
        client.update_record(
            bucket="build-hub",
            collection="archives",
            id="0831d549-0a69-48dd-b240-feef94688d47",
            data={},
        )
        record = client.get_record(
            bucket="build-hub", collection="archives", id="0831d549-0a69-48dd-b240-feef94688d47"
        )
        assert set(record["data"].keys()) == {"id", "last_modified"}
        cmd = "kinto-wizard {} --server={} -D --auth={} --force"
        load_cmd = cmd.format("load {}".format(self.file), self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()
        record = client.get_record(
            bucket="build-hub", collection="archives", id="0831d549-0a69-48dd-b240-feef94688d47"
        )
        assert set(record["data"].keys()) != {"id", "last_modified"}

    def test_round_trip_with_client_wins_and_delete_missing_records(self):
        # Load some data
        cmd = "kinto-wizard {} --server={} --auth={}"
        load_cmd = cmd.format("load {}".format(self.file), self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()

        # Change something that could make the server to fail.
        client = Client(server_url=self.server, auth=tuple(self.auth.split(":")))
        client.create_record(
            bucket="build-hub",
            collection="archives",
            id="8031d549-0a69-48dd-b240-feef94688d47",
            data={},
        )
        cmd = "kinto-wizard {} --server={} -D --auth={} --force --delete-records"
        load_cmd = cmd.format("load {}".format(self.file), self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()
        with pytest.raises(exceptions.KintoException) as exc:
            client.get_record(
                bucket="build-hub",
                collection="archives",
                id="8031d549-0a69-48dd-b240-feef94688d47",
            )
        assert "'Not Found'" in str(exc.value)

    def test_round_trip_with_delete_missing_records_ask_for_confirmation(self):
        # Load some data
        cmd = "kinto-wizard {} --server={} --auth={}"
        load_cmd = cmd.format("load {}".format(self.file), self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()

        # Change something that could make the server to fail.
        client = Client(server_url=self.server, auth=tuple(self.auth.split(":")))
        client.create_record(
            bucket="build-hub",
            collection="archives",
            id="8031d549-0a69-48dd-b240-feef94688d47",
            data={},
        )
        cmd = "kinto-wizard {} --server={} -D --auth={} --delete-records"
        load_cmd = cmd.format("load {}".format(self.file), self.server, self.auth)
        sys.argv = load_cmd.split(" ")

        with mockInput("yes"):
            main()

        with pytest.raises(exceptions.KintoException) as exc:
            client.get_record(
                bucket="build-hub",
                collection="archives",
                id="8031d549-0a69-48dd-b240-feef94688d47",
            )
        assert "'Not Found'" in str(exc.value)

    def test_round_trip_with_delete_missing_records_handle_misconfirmation(self):
        # Load some data
        cmd = "kinto-wizard {} --server={} --auth={}"
        load_cmd = cmd.format("load {}".format(self.file), self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()

        # Change something that could make the server to fail.
        client = Client(server_url=self.server, auth=tuple(self.auth.split(":")))
        client.create_record(
            bucket="build-hub",
            collection="archives",
            id="8031d549-0a69-48dd-b240-feef94688d47",
            data={},
        )
        cmd = "kinto-wizard {} --server={} -D --auth={} --delete-records"
        load_cmd = cmd.format("load {}".format(self.file), self.server, self.auth)
        sys.argv = load_cmd.split(" ")

        with mockInput("no"):
            with pytest.raises(SystemExit):
                main()


class DataRecordsDump(FunctionalTest):
    file = os.getenv("FILE", "tests/kinto-full.yaml")

    def test_round_trip(self):
        # Load some data
        cmd = "kinto-wizard {} --server={} --auth={}"
        load_cmd = cmd.format("load {}".format(self.file), self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        main()

        cmd = "kinto-wizard {} --server={} --auth={} --data --records"
        load_cmd = cmd.format("dump", self.server, self.auth)
        sys.argv = load_cmd.split(" ")
        output = io.StringIO()
        with redirect_stdout(output):
            main()
        output.flush()

        # Check that identical to original file.
        generated = output.getvalue()
        with open(self.file) as f:
            assert_identical(f.read(), generated)


class BucketCollectionSelectionableDump(FunctionalTest):
    file = os.getenv("FILE", "tests/dumps/dump-full.yaml")

    def test_validate(self):
        self.validate()

    def test_round_trip_with_bucket_selection_on_load(self):
        self.load(bucket="natim")
        generated = self.dump()
        with open("tests/dumps/dump-natim.yaml") as f:
            assert_identical(f.read(), generated)

    def test_round_trip_with_bucket_selection(self):
        self.load()
        generated = self.dump(bucket="natim")
        with open("tests/dumps/dump-natim.yaml") as f:
            assert_identical(f.read(), generated)

    def test_round_trip_with_bucket_collection_selection_on_load(self):
        self.load(bucket="natim", collection="toto")
        generated = self.dump()
        with open("tests/dumps/dump-natim-toto-groups.yaml") as f:
            assert_identical(f.read(), generated)

    def test_round_trip_with_bucket_collection_selection(self):
        self.load()
        generated = self.dump(bucket="natim", collection="toto")
        with open("tests/dumps/dump-natim-toto.yaml") as f:
            assert_identical(f.read(), generated)

    def test_round_trip_with_collection_selection_on_load(self):
        self.load(collection="toto")
        generated = self.dump()
        with open("tests/dumps/dump-toto-groups.yaml") as f:
            assert_identical(f.read(), generated)

    def test_round_trip_with_collection_selection(self):
        self.load()
        generated = self.dump(collection="toto")
        with open("tests/dumps/dump-toto.yaml") as f:
            assert_identical(f.read(), generated)

    def test_wizard_can_handle_dates(self):
        self.load(bucket="date")
        generated = self.dump()
        with open("tests/dumps/dump-date.yaml") as f:
            assert_identical(f.read(), generated)


class YAMLReferenceSupportTest(FunctionalTest):
    file = os.getenv("FILE", "tests/dumps/with-references.yaml")

    def test_validate(self):
        self.validate()

    def test_file_can_have_yaml_references(self):
        self.load()

        client = Client(server_url=self.server, auth=tuple(self.auth.split(":")))

        collection = client.get_collection(bucket="main", id="certificates")
        assert "url" in collection["data"]["schema"]["properties"]
        collection = client.get_collection(bucket="main", id="addons")
        assert "url" in collection["data"]["schema"]["properties"]

        # the anchor did not get interpreted as a bucket:
        with self.assertRaises(exceptions.KintoException):
            client.get_collection(bucket="attachment-schema")


class WrongSchemaValidationTest(FunctionalTest):
    file = "tests/dumps/wrong-schema.yaml"

    def test_validate(self):
        self.validate(code=1)


class MiscUpdates(FunctionalTest):
    def get_client(self):
        return Client(server_url=self.server, auth=tuple(self.auth.split(":")))

    def test_validate(self):
        # This dump has a schema that requires `title` field, and a record doesn't have it.
        self.validate(filename="tests/dumps/with-schema-1.yaml", code=1)
        # This dump has a schema that does not require `title` field, so the dump is valid.
        self.validate(filename="tests/dumps/with-schema-2.yaml")

    def test_raises_with_4xx_error_in_batch(self):
        with pytest.raises(exceptions.KintoBatchException):
            self.load(filename="tests/dumps/with-schema-1.yaml")
        records = self.get_client().get_records(bucket="natim", collection="toto")
        assert len(records) == 0

    def test_ignore_batch_4xx_errors_if_specified(self):
        # Raises a KintoBatchException in case of error
        self.load(filename="tests/dumps/with-schema-1.yaml", extra="--ignore-batch-4xx")

    def test_record_updates(self):
        self.load(filename="tests/dumps/with-schema-1.yaml", extra="--ignore-batch-4xx")
        client = self.get_client()
        client.create_record(
            data={"title": "titi", "last_modified": 1496132479110},
            id="e2686bac-c45e-4144-9738-edfeb3d9da6d",
            collection="toto",
            bucket="natim",
        )
        self.load(filename="tests/dumps/with-schema-2.yaml")
        r = client.get_record(
            id="e2686bac-c45e-4144-9738-edfeb3d9da6d", collection="toto", bucket="natim"
        )
        assert r["data"]["title"] == "toto"

    def test_group_updates(self):
        self.load(filename="tests/dumps/with-groups.yaml")
        client = self.get_client()
        client.update_group(
            data={"members": ["alexis", "mathieu", "remy"]}, id="toto", bucket="natim"
        )
        self.load(filename="tests/dumps/with-groups.yaml")
        r = client.get_group(id="toto", bucket="natim")
        assert r["data"]["members"] == ["alexis", "mathieu"]
