"""
A poor man's asynchronous Kinto client.

This is a hack to allow kinto_wizard functionality to call synchronous
kinto-http methods asynchronously without having to keep track of an
event loop and executor.

"""

import functools
from unittest import mock


class AsyncKintoClient(object):
    def __init__(self, client, loop, executor, dry_run=False):
        self.client = client
        self.loop = loop
        self.executor = executor
        self.dry_run = dry_run

    def batch(self):
        if self.dry_run:
            return mock.MagicMock()
        # Don't do anything clever with asynchrony here -- just call
        # the underlying batch() for now
        return self.client.batch()

    def __getattr__(self, attr_name):
        return AsyncKintoMethod(self, attr_name, dry_run=self.dry_run)


class AsyncKintoMethod(object):
    def __init__(self, async_client, method_name, dry_run=False):
        self.async_client = async_client
        self.method_name = method_name
        self.dry_run = dry_run

    def __call__(self, *args, **kwargs):
        client = self.async_client.client
        real_method = getattr(client, self.method_name)
        if not self.dry_run or self.method_name.startswith('get'):
            executor = self.async_client.executor
            loop = self.async_client.loop
            return loop.run_in_executor(
                executor,
                functools.partial(real_method, *args, **kwargs)
            )
