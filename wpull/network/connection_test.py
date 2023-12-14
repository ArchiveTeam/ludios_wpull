# encoding=utf8

import socket
import ssl

import wpull.testing.async_
from wpull.errors import NetworkError, NetworkTimedOut, SSLVerificationError
from wpull.network.connection import Connection
from wpull.testing.badapp import BadAppTestCase, SSLBadAppTestCase


class TestConnection(BadAppTestCase):
    @wpull.testing.async_.async_test()
    def test_connection(self):
        connection = Connection(
            ('127.0.0.1', self.get_http_port()), 'localhost')
        await connection.connect()
        await connection.write(b'GET / HTTP/1.0\r\n\r\n')
        data = await connection.read()

        self.assertEqual(b'hello world!', data[-12:])

        self.assertTrue(connection.closed())

    @wpull.testing.async_.async_test()
    def test_mock_connect_socket_error(self):
        connection = Connection(
            ('127.0.0.1', self.get_http_port()), 'localhost')

        async def mock_func():
            raise socket.error(123, 'Mock error')

        with self.assertRaises(NetworkError):
            await connection.run_network_operation(mock_func())

    @wpull.testing.async_.async_test()
    def test_mock_connect_ssl_error(self):
        connection = Connection(
            ('127.0.0.1', self.get_http_port()), 'localhost')

        async def mock_func():
            raise ssl.SSLError(123, 'Mock error')

        with self.assertRaises(NetworkError):
            await connection.run_network_operation(mock_func())

    @wpull.testing.async_.async_test()
    def test_mock_request_socket_error(self):
        connection = Connection(
            ('127.0.0.1', self.get_http_port()), 'localhost')

        async def mock_func():
            raise ConnectionError(123, 'Mock error')

        with self.assertRaises(NetworkError):
            await connection.run_network_operation(mock_func())

    @wpull.testing.async_.async_test()
    def test_mock_request_ssl_error(self):
        connection = Connection(
            ('127.0.0.1', self.get_http_port()), 'localhost')

        async def mock_func():
            raise ConnectionError(123, 'Mock error')

        with self.assertRaises(NetworkError):
            await connection.run_network_operation(mock_func())

    @wpull.testing.async_.async_test()
    def test_mock_request_certificate_error(self):
        connection = Connection(
            ('127.0.0.1', self.get_http_port()), 'localhost')

        async def mock_func():
            raise ssl.SSLError(1, 'I has a Certificate Error!')

        with self.assertRaises(SSLVerificationError):
            await connection.run_network_operation(mock_func())

    @wpull.testing.async_.async_test()
    def test_mock_request_unknown_ca_error(self):
        connection = Connection(
            ('127.0.0.1', self.get_http_port()), 'localhost')

        async def mock_func():
            raise ssl.SSLError(1, 'Uh oh! Unknown CA!')

        with self.assertRaises(SSLVerificationError):
            await connection.run_network_operation(mock_func())

    @wpull.testing.async_.async_test()
    def test_connect_timeout(self):
        connection = Connection(('10.0.0.0', 1), connect_timeout=2)

        with self.assertRaises(NetworkTimedOut):
            await connection.connect()

    @wpull.testing.async_.async_test()
    def test_read_timeout(self):
        connection = Connection(('127.0.0.1', self.get_http_port()),
                                timeout=0.5)
        await connection.connect()
        await connection.write(b'GET /sleep_long HTTP/1.1\r\n',
                                    drain=False)
        await connection.write(b'\r\n', drain=False)

        data = await connection.readline()
        self.assertEqual(b'HTTP', data[:4])

        while True:
            data = await connection.readline()

            if not data.strip():
                break

        with self.assertRaises(NetworkTimedOut):
            bytes_left = 2
            while bytes_left > 0:
                data = await connection.read(bytes_left)

                if not data:
                    break

                bytes_left -= len(data)

    @wpull.testing.async_.async_test()
    def test_sock_reuse(self):
        connection1 = Connection(('127.0.0.1', self.get_http_port()))
        await connection1.connect()

        connection2 = Connection(
            ('127.0.0.1', self.get_http_port()),
            sock=connection1.writer.get_extra_info('socket')
        )

        await connection2.connect()
        await connection2.write(b'GET / HTTP/1.1\r\n\r\n')

        data = await connection2.readline()
        self.assertEqual(b'HTTP', data[:4])


class TestConnectionSSL(SSLBadAppTestCase):
    @wpull.testing.async_.async_test()
    def test_start_tls(self):
        connection = Connection(('127.0.0.1', self.get_http_port()), timeout=1)

        await connection.connect()

        self.assertFalse(connection.is_ssl)

        ssl_connection = await connection.start_tls()

        self.assertFalse(connection.is_ssl)
        self.assertTrue(ssl_connection.is_ssl)

        await ssl_connection.write(b'GET / HTTP/1.1\r\n\r\n')

        data = await ssl_connection.readline()
        self.assertEqual(b'HTTP', data[:4])



