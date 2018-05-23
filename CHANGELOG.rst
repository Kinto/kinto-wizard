1Changelog
=========

This document describes changes between each past release.

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
