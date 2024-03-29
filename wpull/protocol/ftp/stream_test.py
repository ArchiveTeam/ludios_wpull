import io
import logging

import functools

from wpull.backport.logging import BraceMessage as __
from wpull.network.connection import Connection
from wpull.protocol.ftp.request import Command
from wpull.protocol.ftp.stream import ControlStream, DataStream
from wpull.protocol.ftp.util import parse_address
from wpull.testing.ftp import FTPTestCase
from tornado.testing import gen_test

DEFAULT_TIMEOUT = 30
_logger = logging.getLogger(__name__)


class TestStream(FTPTestCase):
    @gen_test(timeout=30)
    async def test_control_stream(self):
        def log_cb(data_type, data):
            _logger.debug(__('{0}={1}', data_type, data))

        connection = Connection(('127.0.0.1', self.server_port()))
        await connection.connect()

        control_stream = ControlStream(connection)
        control_stream.data_event_dispatcher.add_read_listener(
            functools.partial(log_cb, 'read'))
        control_stream.data_event_dispatcher.add_write_listener(
            functools.partial(log_cb, 'write'))

        reply = await control_stream.read_reply()
        self.assertEqual(220, reply.code)

        await control_stream.write_command(Command('USER', 'smaug'))
        reply = await control_stream.read_reply()
        self.assertEqual(331, reply.code)

        await control_stream.write_command(Command('PASS', 'gold1'))
        reply = await control_stream.read_reply()
        self.assertEqual(230, reply.code)

        await control_stream.write_command(Command('PASV'))
        reply = await control_stream.read_reply()
        self.assertEqual(227, reply.code)
        address = parse_address(reply.text)

        data_connection = Connection(address)
        await data_connection.connect()

        data_stream = DataStream(data_connection)

        await control_stream.write_command(Command('RETR', 'example (copy).txt'))
        reply = await control_stream.read_reply()
        self.assertEqual(150, reply.code)

        my_file = io.BytesIO()

        await data_stream.read_file(my_file)

        reply = await control_stream.read_reply()
        self.assertEqual(226, reply.code)

        self.assertEqual(
            'The real treasure is in Smaug’s heart 💗.\n',
            my_file.getvalue().decode('utf-8')
            )
