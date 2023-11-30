Changelog
=========

This document describes changes between each past release.

4.0.2 (2023-11-30)
------------------

**Internal Changes**

- Remove usage of deprecated ``ruamel.yaml`` loading and dumping function (now requires >0.15, released in 2019) (#296)
- Fix tests coverage.


4.0.1 (2018-12-10)
------------------

**Bug fixes**

- Handle Draftv4 schema validation for empty required.


4.0.0 (2018-12-10)
------------------

**Breaking changes**

- ``kinto-wizard load`` now expects to find a ``buckets:`` root level in
  the YAML file.  And ``kinto-wizard dump`` will now add it (fixes #59)

**New feature**

- Add a ``validate`` command to run JSON schema validation on the records
  locally. (fixes #61)

**Internal changes**

- To ease the transition between kinto-wizard 3 and kinto-wizard 4,
  handle both for a couple of releases. (#64)


3.0.0 (2018-10-17)
------------------

**Breaking changes**

- Upgrade to kinto-http.py 10.0 means that the batch will fail if one
  of the server responses has a 4XX status, use the
  ``--ignore-batch-4xx`` to keep the previous behaviour.

**New features**

- Add an ``--ignore-batch-4xx`` option to explicitly ask for silent
  4xx errors.

**Bug fixes**

- Handle YAML date and datetime values. (#51)

**Internal changes**

- Add test for YAML node anchors support (#52)
  See https://en.wikipedia.org/wiki/YAML#Advanced_components


2.4.0 (2018-05-23)
------------------

- Add a ``--dry-run`` for the load command to see how many records
  would be deleted. (#46)
- Add a ``--delete-record`` to delete the existing records that are
  not in the YAML file. (#47)


2.3.0 (2017-10-04)
------------------

- Add ``--data`` and ``--records`` options to be able to dump objects
  data without dumping records. (#33)


2.2.0 (2017-09-01)
------------------

**New features**

- Use ``asyncio`` to add parallelism to the ``load`` command (#18).


2.1.0 (2017-06-28)
------------------

**New features**

- Add logger configuration for kinto-http.py (#26)
- Add an option to force the update with a CLIENT_WINS strategy (#28)
- Add an option to select the bucket or collection to export (#30)


2.0.0 (2017-05-22)
------------------

**Breaking changes**

- Upgrade to kinto-http 8.0.0 with Python 3.5+ support.
- The ``--full`` option of the ``dump`` command now outputs records (#16)

**New features**

- The ``load`` command now supports records (#16)


1.0.0 (2016-11-22)
------------------

**Initial version**

- Supports dumping/loading groups and permissions from/to a YAML file.
