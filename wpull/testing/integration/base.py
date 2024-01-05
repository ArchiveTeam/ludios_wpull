import logging
from http import cookiejar

import asyncio
import tornado.web
from tornado.testing import AsyncHTTPSTestCase
import tornado.ioloop

from unittest import IsolatedAsyncioTestCase
from wpull.testing.badapp import BadAppTestCase
from wpull.testing.ftp import FTPTestCase
from wpull.testing.goodapp import GoodAppTestCase
from wpull.testing.util import TempDirMixin
# from wpull.testing.async_ import AsyncHTTPSTestCase


class AppTestCase(IsolatedAsyncioTestCase, TempDirMixin):
    def setUp(self):
        self._original_cookiejar_debug = cookiejar.debug
        cookiejar.debug = True
        super().setUp()
        self.original_loggers = list(logging.getLogger().handlers)
        self.set_up_temp_dir()

    def tearDown(self):
        super().tearDown()
        cookiejar.debug = self._original_cookiejar_debug

        for handler in list(logging.getLogger().handlers):
            if handler not in self.original_loggers:
                logging.getLogger().removeHandler(handler)

        self.tear_down_temp_dir()


class HTTPGoodAppTestCase(GoodAppTestCase, TempDirMixin):
    def setUp(self):
        self._original_cookiejar_debug = cookiejar.debug
        cookiejar.debug = True
        super().setUp()
        self.original_loggers = list(logging.getLogger().handlers)
        self.set_up_temp_dir()

    def tearDown(self):
        GoodAppTestCase.tearDown(self)
        cookiejar.debug = self._original_cookiejar_debug

        for handler in list(logging.getLogger().handlers):
            if handler not in self.original_loggers:
                logging.getLogger().removeHandler(handler)

        self.tear_down_temp_dir()


class SimpleHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(b'OK')


class HTTPSSimpleAppTestCase(IsolatedAsyncioTestCase, AsyncHTTPSTestCase, TempDirMixin):
    def setUp(self):
        IsolatedAsyncioTestCase.setUp(self)
        AsyncHTTPSTestCase.setUp(self)
        self.set_up_temp_dir()

    def tearDown(self):
        AsyncHTTPSTestCase.tearDown(self)
        IsolatedAsyncioTestCase.tearDown(self)
        self.tear_down_temp_dir()

    def get_app(self):
        return tornado.web.Application([
            (r'/', SimpleHandler)
        ])


class HTTPBadAppTestCase(BadAppTestCase, TempDirMixin):
    def setUp(self):
        BadAppTestCase.setUp(self)
        self.set_up_temp_dir()

    def tearDown(self):
        BadAppTestCase.tearDown(self)
        self.tear_down_temp_dir()


class FTPAppTestCase(FTPTestCase, TempDirMixin):
    def setUp(self):
        super().setUp()
        self.original_loggers = list(logging.getLogger().handlers)
        self.set_up_temp_dir()

    def tearDown(self):
        FTPTestCase.tearDown(self)

        for handler in list(logging.getLogger().handlers):
            if handler not in self.original_loggers:
                logging.getLogger().removeHandler(handler)

        self.tear_down_temp_dir()


async def tornado_future_adapter(future):
    event = asyncio.Event()

    future.add_done_callback(lambda dummy: event.set())

    await event.wait()

    return future.result()
