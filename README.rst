kinto-wizard
============

Kinto Minion is a tool that let you setup an entire Kinto server by
loading a Yaml file.

You can define any Kinto object (bucket, collection, groups, records)
and configure its properties and permissions.

[Read more information about the file structure](https://github.com/Kinto/kinto/wiki/Handling-permission-on-a-Kinto-Server)


Installation
------------

The last release
~~~~~~~~~~~~~~~~

.. code-block:: bash

    pip install kinto-wizard


The development version
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    pip install kinto-wizard


How to use it?
--------------

.. code-block:: bash

    kinto-wizard \
	    --server https://kinto-writer.stage.mozaws.net/v1 \
		--auth admin:credentials \
		permission-config.yml

