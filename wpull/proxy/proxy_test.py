import io


import asyncio
import tornado.testing

from wpull.protocol.http.client import Client
from wpull.protocol.http.request import Request
from wpull.proxy.client import HTTPProxyConnectionPool
from wpull.proxy.server import HTTPProxyServer
import wpull.testing.badapp
import wpull.testing.goodapp
import wpull.testing.async_
from tornado.testing import gen_test


# FIXME: Test currently fails due internal server returning: CONNECT: 501 CONNECT is intentionally not supported
# See: https://github.com/ArchiveTeam/wpull/pull/348
# See: https://github.com/ArchiveTeam/wpull/pull/348/commits/561380774baf5fd44990d16d64f545259c7385a1


# class Mixin:
#     @gen_test(timeout=30)
#     async def test_basic_requests(self):
#         proxy_http_client = Client()
#         proxy_server = HTTPProxyServer(proxy_http_client)
#         proxy_socket, proxy_port = tornado.testing.bind_unused_port()

#         await asyncio.start_server(proxy_server, sock=proxy_socket)

#         connection_pool = HTTPProxyConnectionPool(('127.0.0.1', proxy_port))
#         http_client = Client(connection_pool=connection_pool)

#         for dummy in range(3):
#             with http_client.session() as session:
#                 response = await session.start(Request(self.get_url('/')))
#                 self.assertEqual(200, response.status_code)

#                 file = io.BytesIO()
#                 await session.download(file=file)
#                 data = file.getvalue().decode('ascii', 'replace')
#                 self.assertTrue(data.endswith('</html>'))

#             with http_client.session() as session:
#                 response = await session.start(Request(
#                     self.get_url('/always_error')))
#                 self.assertEqual(500, response.status_code)
#                 self.assertEqual('Dragon In Data Center', response.reason)

#                 file = io.BytesIO()
#                 await session.download(file=file)
#                 data = file.getvalue().decode('ascii', 'replace')
#                 self.assertEqual('Error', data)


# class TestProxy(wpull.testing.goodapp.GoodAppTestCase, Mixin):
#     pass


# class TestProxySSL(wpull.testing.goodapp.GoodAppHTTPSTestCase, Mixin):
#     pass    # FIXME: Broken unittest
    # Python 3.11+ uses the _ensure_fd_no_transport method that 
    # prevents multiple transports from using a single socket
    # Reference: https://github.com/python/cpython/issues/88968

    # @gen_test(timeout=30)
    # async def test_sock_reuse(self):

    #     connection1 = Connection(('127.0.0.1', self.get_http_port()))
    #     await connection1.connect()

    #     connection2 = Connection(
    #         ('127.0.0.1', self.get_http_port()),
    #         sock=connection1.writer.get_extra_info('socket')
    #     )

    #     await connection2.connect()
    #     await connection2.write(b'GET / HTTP/1.1\r\n\r\n')

    #     data = await connection2.readline()
    #     self.assertEqual(b'HTTP', data[:4])

    #     connection1.close()
    #     connection2.close()