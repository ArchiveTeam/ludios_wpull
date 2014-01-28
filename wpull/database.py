# encoding=utf-8
'''URL Tables.'''

import abc
import collections
import sqlite3


class DatabaseError(Exception):
    '''Any database error.'''
    pass


class NotFound(DatabaseError):
    '''Item not found in the table.'''
    pass


class Status(object):
    '''URL status.'''
    todo = 'todo'
    in_progress = 'in_progress'
    done = 'done'
    error = 'error'
    skipped = 'skipped'


class URLRecord(sqlite3.Row, object):
    '''An entry in the table.'''
    def __getattribute__(self, key):
        try:
            return self[key]
        except (IndexError, KeyError):
            return super().__getattribute__(key)

    def __repr__(self):
        return 'Record{0}'.format(tuple(self))

    def to_dict(self):
        return dict([(key, self[key]) for key in self.keys()])


class BaseURLTable(collections.Mapping, object, metaclass=abc.ABCMeta):
    '''URL table.'''
    def __init__(self):
        super().__init__()

    @abc.abstractmethod
    def add(self, urls, **kwargs):
        '''Add the URLs to the table.

        Args:
            urls: An iterable of URL strings
            kwargs: Additional values to be saved for all the URLs
        '''
        pass

    @abc.abstractmethod
    def get_and_update(self, status, new_status=None, level=None):
        '''Find a URL, mark it in progress, and return it.'''
        pass

    @abc.abstractmethod
    def update(self, url, increment_try_count=False, **kwargs):
        '''Set values for the URL.'''
        pass

    @abc.abstractmethod
    def count(self):
        '''Return the number of URLs in the table.'''
        pass

    @abc.abstractmethod
    def release(self):
        '''Mark any ``in_progress`` URLs to ``todo`` status.'''
        pass


class SQLiteURLTable(BaseURLTable):
    '''URL table with SQLite storage.

    Args:
        path: A SQLite filename
    '''
    def __init__(self, path=':memory:'):
        super().__init__()
        self._connection = sqlite3.connect(path)
        self._apply_pragmas()
        self._create_tables()
        self._create_indexes()
        self._connection.row_factory = URLRecord

    def _apply_pragmas(self):
        '''Set SQLite pragmas.

        Write-ahead logging is used.
        '''
        self._connection.execute('PRAGMA journal_mode=WAL')

    def _create_tables(self):
        '''Create the table.'''
        self._connection.execute(
            '''CREATE TABLE IF NOT EXISTS urls
            (
                url TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                try_count INTEGER NOT NULL DEFAULT 0,
                level INTEGER NOT NULL DEFAULT 0,
                top_url TEXT,
                status_code INTEGER,
                referrer TEXT,
                inline INTEGER,
                link_type TEXT,
                url_encoding TEXT,
                request BLOB
            )
            '''
        )

    def _create_indexes(self):
        '''Create indexes.

        An index is built on the url status column.
        '''
        self._connection.execute(
            '''CREATE INDEX IF NOT EXISTS url_status_index ON urls (status)'''
        )

    def __getitem__(self, url):
        query = '''SELECT * FROM urls WHERE url = ?'''
        cursor = self._connection.execute(query, (url,))
        result = cursor.fetchone()

        if not result:
            raise IndexError()
        else:
            return result

    def __iter__(self):
        query = '''SELECT * FROM urls'''
        return self._connection.execute(query)

    def __len__(self):
        query = '''SELECT count(rowid) FROM urls'''
        cursor = self._connection.execute(query)
        return cursor.fetchone()[0]

    def add(self, urls, **kwargs):
        assert not isinstance(urls, (str, bytes))

        query = '''INSERT OR IGNORE INTO urls (url, status)
            VALUES (?, ?)'''

        with self._connection:
            for url in urls:
                assert isinstance(url, str)
                self._connection.execute(query, (url, Status.todo))
            # XXX: If inserts and updates are mixed together, then rows are
            # mysteriously lost.
            for url in urls:
                for key, value in kwargs.items():
                    query = '''UPDATE urls
                        SET {0} = ? WHERE url = ?'''.format(key)
                    self._connection.execute(query, (value, url))

    def get_and_update(self, status, new_status=None, level=None):
        with self._connection:
            if level is None:
                query = '''SELECT * FROM urls WHERE status = ? LIMIT 1'''
                row = self._connection.execute(query, (status,)).fetchone()
            else:
                query = '''SELECT * FROM urls WHERE status = ? AND level < ?
                    LIMIT 1'''
                row = self._connection.execute(query, (status, level)
                    ).fetchone()

            if not row:
                raise NotFound()

            if new_status:
                update_query = '''UPDATE urls SET status = ? WHERE url = ?'''
                self._connection.execute(update_query, (new_status, row.url))

                row = self[row.url]

            return row

    def update(self, url, increment_try_count=False, **kwargs):
        assert isinstance(url, str)

        with self._connection:
            if increment_try_count:
                query = '''UPDATE urls SET try_count = try_count + 1
                    WHERE url = ?'''
                self._connection.execute(query, (url,))

            for key, value in kwargs.items():
                query = '''UPDATE urls SET {0} = ? WHERE url = ?'''.format(key)
                self._connection.execute(query, (value, url))

    def count(self):
        query = '''SELECT count(rowid) FROM urls'''
        return self._connection.execute(query).fetchone()[0]

    def release(self):
        query = '''UPDATE urls SET status = ? WHERE status = ? '''
        self._connection.execute(query, (Status.todo, Status.in_progress))


class URLTable(SQLiteURLTable):
    '''The default URL table implementation.'''
    pass
