Changelog
=========

This document describes changes between each past release.

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
