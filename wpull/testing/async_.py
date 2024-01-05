from tornado.platform.asyncio import BaseAsyncIOLoop
import asyncio
import os
import functools
from tornado.testing import bind_unused_port, get_async_test_timeout
import unittest
from tornado.httpclient import AsyncHTTPClient
from tornado.httpserver import HTTPServer
from tornado.web import Application
from tornado.ioloop import IOLoop
from typing import Any

# class AsyncTestCase(unittest.TestCase):
#     def setUp(self):
#         self.event_loop = asyncio.new_event_loop()
#         self.event_loop.set_debug(True)
#         asyncio.set_event_loop(self.event_loop)

#     def tearDown(self):
#         self.event_loop.stop()
#         self.event_loop.close()



def async_test(func=None, timeout=30):
    # tornado.testing
    def wrap(f):
        @functools.wraps(f)
        async def wrapper(self):
            await asyncio.wait_for(f(self), timeout=timeout)
        return wrapper

    if func is not None:
        # Used like:
        #     @gen_test
        #     def f(self):
        #         pass
        return wrap(func)
    else:
        # Used like @gen_test(timeout=10)
        return wrap

class AsyncHTTPTestCase(unittest.IsolatedAsyncioTestCase):
    # Native unittest based replacement for the deprecated Tornado AsyncHTTPTestCase
    # This will be replaced (hopefully) by an official Tornado implementation
    def setUp(self) -> None:
        super().setUp()
        sock, port = bind_unused_port()
        self.__port = port

        self.http_client = self.get_http_client()
        self._app = self.get_app()
        self.http_server = self.get_http_server()
        self.http_server.add_sockets([sock])

    def get_http_client(self) -> AsyncHTTPClient:
        return AsyncHTTPClient()

    def get_http_server(self) -> HTTPServer:
        return HTTPServer(self._app, **self.get_httpserver_options())

    def get_app(self) -> Application:
        """Should be overridden by subclasses to return a
        `tornado.web.Application` or other `.HTTPServer` callback.
        """
        raise NotImplementedError()


    def get_httpserver_options(self) -> dict[str, Any]:
        """May be overridden by subclasses to return additional
        keyword arguments for the server.
        """
        return {}

    def get_http_port(self) -> int:
        """Returns the port used by the server.

        A new port is chosen for each test.
        """
        return self.__port

    def get_protocol(self) -> str:
        return "http"

    def get_url(self, path: str) -> str:
        """Returns an absolute url for the given path on the test server."""
        return "%s://127.0.0.1:%s%s" % (self.get_protocol(), self.get_http_port(), path)

    def tearDown(self) -> None:
        self.http_server.stop()
        io_loop = IOLoop.current()
        io_loop.run_sync(
            self.http_server.close_all_connections, timeout=get_async_test_timeout()
        )
        self.http_client.close()
        del self.http_server
        del self._app
        super().tearDown()

class AsyncHTTPSTestCase(AsyncHTTPTestCase):
    """A test case that starts an HTTPS server.

    Interface is generally the same as `AsyncHTTPTestCase`.
    """

    def get_http_client(self) -> AsyncHTTPClient:
        return AsyncHTTPClient(force_instance=True, defaults=dict(validate_cert=False))

    def get_httpserver_options(self) -> dict[str, Any]:
        return dict(ssl_options=self.get_ssl_options())

    def get_ssl_options(self) -> dict[str, Any]:
        """May be overridden by subclasses to select SSL options.

        By default includes a self-signed testing certificate.
        """
        return AsyncHTTPSTestCase.default_ssl_options()

    @staticmethod
    def default_ssl_options() -> dict[str, Any]:
        # Testing keys were generated with:
        # openssl req -new -keyout tornado/test/test.key \
        #                     -out tornado/test/test.crt -nodes -days 3650 -x509
        module_dir = os.path.dirname(__file__)
        return dict(
            certfile=os.path.join(module_dir, "test", ""),
            keyfile=os.path.join(module_dir, "test", "test.key"),
        )

    def get_protocol(self) -> str:
        return "https"



class TornadoAsyncIOLoop(BaseAsyncIOLoop):
    def initialize(self, event_loop):
        super().initialize(event_loop, close_loop=False)
