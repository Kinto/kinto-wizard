kinto-wizard
============

|pypi| |ci| |coverage|

.. |pypi| image:: https://img.shields.io/pypi/v/kinto-wizard.svg
    :target: https://pypi.python.org/pypi/kinto-wizard
.. |ci| image::  https://img.shields.io/github/actions/workflow/status/Kinto/kinto-wizard/test.yml?branch=main
    :target: https://github.com/Kinto/kinto-wizard/actions
.. |coverage| image:: https://coveralls.io/repos/github/Kinto/kinto-wizard/badge.svg?branch=main
    :target: https://coveralls.io/github/Kinto/kinto-wizard?branch=main

kinto-wizard is a tool that lets you setup an entire Kinto server from
a Yaml file, or inspect an existing server and output a Yaml file.

You can define Kinto objects (bucket, collection, groups, records)
and configure their attributes and permissions.

`Read more information about the file structure <https://github.com/Kinto/kinto/wiki/Handling-permission-on-a-Kinto-Server>`_


Installation
------------

Use pip:

.. code-block:: bash

    $ pip install kinto-wizard


How to use it?
--------------

Load
~~~~

.. code-block:: bash

    kinto-wizard load \
        --server https://kinto-writer.stage.mozaws.net/v1 \
        --auth admin:credentials \
        new-config.yml

Dump
~~~~

.. code-block:: bash

    kinto-wizard dump \
        --server https://kinto-writer.stage.mozaws.net/v1 \
        --auth admin:credentials \
        > current-config.yml

The dump command also accepts these options:

* ``--data`` - Include buckets, collections and groups data (attachments, schemas, display fields, uischema etc.).
* ``--records`` - Include collections` records.
* ``--full`` - Combination of data and records.

Validate a dump
---------------

The way Kinto works is by letting you change a collection schema but
won't enforce the new schema for existing records.

When you dump a collection and its records, you can end-up having
records that Kinto won't let you upload back because the schema
changed and they are invalid with the current schema.

This can lead to unexpected behavior on loading time which is a bit
cumbersome because depending of the size of the file you are loading,
it can takes a long time before getting an actual error.

In order to fix the file before loading, you can use the validate
command that would give you the error Kinto would return if you were
to load the file on a Kinto server.


.. code-block:: bash

    kinto-wizard validate current-config.yml


Development
-----------

See `contributing docs <./.github/CONTRIBUTING.md>`_
