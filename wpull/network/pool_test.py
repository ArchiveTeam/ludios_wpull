import asyncio

import functools

import wpull.testing.async_
from wpull.network.connection import Connection
from wpull.network.dns import Resolver
from wpull.network.pool import ConnectionPool, HostPool, HappyEyeballsTable
from wpull.testing.badapp import BadAppTestCase


class TestConnectionPool(BadAppTestCase):
    @wpull.testing.async_.async_test()
    def test_basic_acquire(self):
        pool = ConnectionPool(max_host_count=2)

        conn1 = await pool.acquire('localhost', self.get_http_port())
        conn2 = await pool.acquire('localhost', self.get_http_port())

        await pool.release(conn1)
        await pool.release(conn2)

        conn3 = await pool.acquire('localhost', self.get_http_port())
        conn4 = await pool.acquire('localhost', self.get_http_port())

        await pool.release(conn3)
        await pool.release(conn4)

    @wpull.testing.async_.async_test()
    def test_session(self):
        pool = ConnectionPool()

        for dummy in range(10):
            session = await \
                pool.session('localhost', self.get_http_port())
            with session as connection:
                if connection.closed():
                    await connection.connect()

        self.assertEqual(1, len(pool.host_pools))
        host_pool = list(pool.host_pools.values())[0]
        self.assertIsInstance(host_pool, HostPool)
        self.assertEqual(1, host_pool.count())

    @wpull.testing.async_.async_test()
    def test_host_max_limit(self):
        pool = ConnectionPool(max_host_count=2)

        await pool.acquire('localhost', self.get_http_port())
        await pool.acquire('localhost', self.get_http_port())

        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(
                pool.acquire('localhost', self.get_http_port()),
                0.1
            )

    @wpull.testing.async_.async_test()
    def test_at_host_max_limit_cycling(self):
        pool = ConnectionPool(max_host_count=10, max_count=10)

        async def con_fut():
            session = await pool.session('localhost', self.get_http_port())

            with session as connection:
                if connection.closed():
                    await connection.connect()

        futs = [con_fut() for dummy in range(10)]

        await asyncio.wait(futs)

        self.assertEqual(1, len(pool.host_pools))
        connection_pool_entry = list(pool.host_pools.values())[0]
        self.assertIsInstance(connection_pool_entry, HostPool)
        self.assertGreaterEqual(10, connection_pool_entry.count())

    @wpull.testing.async_.async_test()
    def test_over_host_max_limit_cycling(self):
        pool = ConnectionPool(max_host_count=10, max_count=10)

        async def con_fut():
            session = await \
                pool.session('localhost', self.get_http_port())

            with session as connection:
                if connection.closed():
                    await connection.connect()

        futs = [con_fut() for dummy in range(20)]

        await asyncio.wait(futs)

        self.assertEqual(1, len(pool.host_pools))
        connection_pool_entry = list(pool.host_pools.values())[0]
        self.assertIsInstance(connection_pool_entry, HostPool)
        self.assertGreaterEqual(10, connection_pool_entry.count())

    @wpull.testing.async_.async_test()
    def test_multiple_hosts(self):
        pool = ConnectionPool(max_host_count=5, max_count=20)

        for port in range(10):
            session = await pool.session('localhost', port)

            with session as connection:
                self.assertTrue(connection)

    @wpull.testing.async_.async_test()
    def test_clean(self):
        pool = ConnectionPool(max_host_count=2)

        conn1 = await pool.acquire('localhost', self.get_http_port())
        conn2 = await pool.acquire('localhost', self.get_http_port())

        await pool.release(conn1)
        await pool.release(conn2)
        await pool.clean()

        self.assertEqual(0, len(pool.host_pools))

    @wpull.testing.async_.async_test()
    def test_connection_pool_release_clean_race_condition(self):
        pool = ConnectionPool(max_host_count=1)

        connection = await pool.acquire('127.0.0.1', 1234)
        connection_2_task = asyncio.ensure_future(pool.acquire('127.0.0.1', 1234))
        await asyncio.sleep(0.01)
        pool.no_wait_release(connection)
        await pool.clean(force=True)
        connection_2 = await connection_2_task

        # This line should not KeyError crash:
        await pool.release(connection_2)

    @wpull.testing.async_.async_test()
    def test_happy_eyeballs(self):
        connection_factory = functools.partial(Connection, connect_timeout=10)
        resolver = Resolver()
        pool = ConnectionPool(resolver=resolver,
                              connection_factory=connection_factory)

        conn1 = await pool.acquire('google.com', 80)
        conn2 = await pool.acquire('google.com', 80)

        await conn1.connect()
        await conn2.connect()
        conn1.close()
        conn2.close()

        await pool.release(conn1)
        await pool.release(conn2)

        conn3 = await pool.acquire('google.com', 80)

        await conn3.connect()
        conn3.close()

        await pool.release(conn3)

    def test_happy_eyeballs_table(self):
        table = HappyEyeballsTable()

        self.assertIsNone(table.get_preferred('127.0.0.1', '::1'))

        table.set_preferred('::1', '127.0.0.1', '::1')

        self.assertEqual('::1', table.get_preferred('127.0.0.1', '::1'))
        self.assertEqual('::1', table.get_preferred('::1', '127.0.0.1'))

        table.set_preferred('::1', '::1', '127.0.0.1')

        self.assertEqual('::1', table.get_preferred('127.0.0.1', '::1'))
        self.assertEqual('::1', table.get_preferred('::1', '127.0.0.1'))

        table.set_preferred('127.0.0.1', '::1', '127.0.0.1')

        self.assertEqual('127.0.0.1', table.get_preferred('127.0.0.1', '::1'))
        self.assertEqual('127.0.0.1', table.get_preferred('::1', '127.0.0.1'))
