import unittest

from tornado.platform.asyncio import BaseAsyncIOLoop
import asyncio


# http://stackoverflow.com/q/23033939/1524507
class AsyncTestCase(unittest.TestCase):
    def setUp(self):
        self.event_loop = asyncio.new_event_loop()
        self.event_loop.set_debug(True)
        asyncio.set_event_loop(self.event_loop)

    def tearDown(self):
        self.event_loop.stop()
        self.event_loop.close()


def async_test(func=None, timeout=30):
    # gen_test uses environment variable ASYNC_TEST_TIMEOUT as default if set,
    # otherwise 5 seconds
    return func
    # return gen_test(func, timeout)


class TornadoAsyncIOLoop(BaseAsyncIOLoop):
    def initialize(self, event_loop):
        super().initialize(event_loop, close_loop=False)
