"""
A poor man's asynchronous Kinto client.

This is a hack to allow kinto_wizard functionality to call synchronous
kinto-http methods asynchronously without having to keep track of an
event loop and executor.

"""

import functools


class AsyncKintoClient(object):
    def __init__(self, client, loop, executor):
        self.client = client
        self.loop = loop
        self.executor = executor

    def batch(self):
        # Don't do anything clever with asynchrony here -- just call
        # the underlying batch() for now
        return self.client.batch()

    def __getattr__(self, attr_name):
        return AsyncKintoMethod(self, attr_name)


class AsyncKintoMethod(object):
    def __init__(self, async_client, method_name):
        self.async_client = async_client
        self.method_name = method_name

    def __call__(self, *args, **kwargs):
        client = self.async_client.client
        real_method = getattr(client, self.method_name)
        executor = self.async_client.executor
        loop = self.async_client.loop
        return loop.run_in_executor(
            executor,
            functools.partial(real_method, *args, **kwargs)
        )
