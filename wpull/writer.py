# encoding=utf-8
'''Document writers.'''
# Wpull. Copyright 2013-2014: Christopher Foo. License: GPL v3.
import abc
import base64
import collections
import email.utils
import gettext
import http.client
import itertools
import logging
import os
import shutil
import time
import urllib.parse

import wpull.util


_ = gettext.gettext
_logger = logging.getLogger(__name__)


class BaseWriter(object, metaclass=abc.ABCMeta):
    '''Base class for document writers.'''
    @abc.abstractmethod
    def session(self):
        '''Return an instance of :class:`BaseWriterSession`.'''
        pass


class BaseWriterSession(object, metaclass=abc.ABCMeta):
    '''Base class for a single document to be written.'''
    @abc.abstractmethod
    def process_request(self, request):
        '''Rewrite the request if needed.

        Args:
            request: :class:`.http.request.Request`

        This function is called by a Processor after it has created the
        Request, but before submitting it to the Engine.

        Returns:
            The original Request or a modified Request
        '''
        pass

    @abc.abstractmethod
    def process_response(self, response):
        '''Do any processing using the given response if needed.

        This function is called by a Processor before any response or error
        handling is done.
        '''
        pass

    @abc.abstractmethod
    def save_document(self, response):
        '''Process and save the document.

        This function is called by a Processor once the Processor deemed
        the document should be saved (i.e., a "200 OK" response).

        Returns:
            str: The filename of the document.
        '''
        pass

    @abc.abstractmethod
    def discard_document(self, response):
        '''Don't save the document.

        This function is called by a Processor once the Processor deemed
        the document should be deleted (i.e., a "404 Not Found" response).
        '''
        pass

    @abc.abstractmethod
    def extra_resource_path(self, suffix):
        '''Return a filename suitable for saving extra resources.

        Returns:
            str, None
        '''
        pass


class BaseFileWriter(BaseWriter):
    '''Base class for saving documents to disk.

    Args:
        path_name: :class:`PathNamer`
        file_continuing: If True, the writer will modifiy requests to fetch
            the remaining portion of the file
        headers_included: If True, the writer will include the HTTP header
            responses on top of the document
        local_timestamping: If True, the writer will set the Last-Modified
            timestamp on downloaded files
    '''
    def __init__(self, path_namer, file_continuing=False,
    headers_included=False, local_timestamping=True):
        self._path_namer = path_namer
        self._file_continuing = file_continuing
        self._headers_included = headers_included
        self._local_timestamping = local_timestamping

    @abc.abstractproperty
    def session_class(self):
        '''Return the class of File Writer Session.

        This should be overridden by subclasses.
        '''
        pass

    def session(self):
        '''Return the File Writer Session.'''
        return self.session_class(
            self._path_namer,
            self._file_continuing,
            self._headers_included,
            self._local_timestamping,
        )


class BaseFileWriterSession(BaseWriterSession):
    '''Base class for File Writer Sessions.'''
    def __init__(self, path_namer, file_continuing,
    headers_included, local_timestamping):
        self._path_namer = path_namer
        self._file_continuing = file_continuing
        self._headers_included = headers_included
        self._local_timestamping = local_timestamping
        self._filename = None

    @classmethod
    def open_file(cls, filename, response, mode='wb+'):
        '''Open a file object on to the Response Body.

        Args:
            filename: The path where the file is to be saved
            response: :class:`.http.request.Response`
            mode: The file mode

        This function will create the directories if not exist.
        '''
        _logger.debug('Saving file to {0}, mode={1}.'.format(
            filename, mode))

        dir_path = os.path.dirname(filename)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)

        response.body.content_file = open(filename, mode)

    @classmethod
    def set_timestamp(cls, filename, response):
        '''Set the Last-Modified timestamp onto the given file.

        Args:
            filename: The path of the file
            response: :class:`.http.request.Response`
        '''
        last_modified = response.fields.get('Last-Modified')

        if not last_modified:
            return

        try:
            last_modified = email.utils.parsedate(last_modified)
        except ValueError:
            _logger.exception('Failed to parse date.')
            return

        last_modified = time.mktime(last_modified)

        os.utime(filename, (time.time(), last_modified))

    @classmethod
    def save_headers(cls, filename, response):
        '''Prepend the HTTP response header to the file.

        Args:
            filename: The path of the file
            response: :class:`.http.request.Response`
        '''
        new_filename = filename + '-new'

        with open('wb') as new_file:
            new_file.write(response.header())

            with wpull.util.reset_file_offset(response.body.content_file):
                response.body.content_file.seek(0)
                shutil.copyfileobj(response.body.content_file, new_file)

        os.remove(filename)
        os.rename(new_filename, filename)

    def process_request(self, request):
        if not self._filename:
            self._filename = self._compute_filename(request)

            if self._file_continuing and self._filename:
                self._process_file_continue_request(request)

        return request

    def _compute_filename(self, request):
        '''Get the appropriate filename from the request.'''
        return self._path_namer.get_filename(request.url_info)

    def _process_file_continue_request(self, request):
        '''Modify the request to resume downloading file.'''
        if os.path.exists(self._filename):
            size = os.path.getsize(self._filename)
            request.fields['Range'] = 'bytes={0}-'.format(size)

            _logger.debug('Continue file from {0}.'.format(size))
        else:
            _logger.debug('No file to continue.')

    def process_response(self, response):
        if not self._filename:
            return

        code = response.status_code

        if self._file_continuing:
            self._process_file_continue_response(response)
        elif 200 <= code <= 299 or 400 <= code:
            self.open_file(self._filename, response)

    def _process_file_continue_response(self, response):
        '''Process a partial content response.'''
        code = response.status_code

        if code == http.client.PARTIAL_CONTENT:
            self.open_file(self._filename, response, mode='ab+')
        else:
            raise IOError(
                _('Could not continue file download: {filename}.')\
                    .format(filename=self._filename))

    def save_document(self, response):
        if self._filename and os.path.exists(self._filename):
            if self._headers_included:
                self.save_headers(self._filename, response)

            if self._local_timestamping:
                self.set_timestamp(self._filename, response)

            return self._filename

    def discard_document(self, response):
        if self._filename and os.path.exists(self._filename):
            os.remove(self._filename)

    def extra_resource_path(self, suffix):
        if self._filename:
            return self._filename + suffix


class OverwriteFileWriter(BaseFileWriter):
    '''File writer that overwrites files.'''
    @property
    def session_class(self):
        return OverwriteFileWriterSession


class OverwriteFileWriterSession(BaseFileWriterSession):
    pass


class IgnoreFileWriter(BaseFileWriter):
    '''File writer that ignores files that already exist.'''
    @property
    def session_class(self):
        return IgnoreFileWriterSession


class IgnoreFileWriterSession(BaseFileWriterSession):
    def process_request(self, request):
        if not self._filename or not os.path.exists(self._filename):
            return super().process_request(request)


class AntiClobberFileWriter(BaseFileWriter):
    '''File writer that downloads to a new filename if the original exists.'''
    @property
    def session_class(self):
        return AntiClobberFileWriterSession


class AntiClobberFileWriterSession(BaseFileWriterSession):
    def _compute_filename(self, request):
        original_filename = self._path_namer.get_filename(request.url_info)
        candidate_filename = original_filename

        for suffix in itertools.count():
            if suffix:
                candidate_filename = '{0}.{1}'.format(original_filename,
                    suffix)

            if not os.path.exists(candidate_filename):
                return candidate_filename


class TimestampingFileWriter(BaseFileWriter):
    '''File writer that only downloads newer files from the server.'''
    @property
    def session_class(self):
        return TimestampingFileWriterSession


class TimestampingFileWriterSession(BaseFileWriterSession):
    def process_request(self, request):
        request = super().process_request(request)

        orig_file = '{0}.orig'.format(self._filename)

        if os.path.exists(orig_file):
            modified_time = os.path.getmtime(orig_file)
        elif os.path.exists(self._filename):
            modified_time = os.path.getmtime(self._filename)
        else:
            modified_time = None

        _logger.debug('Checking for last modified={0}.'.format(modified_time))

        if modified_time:
            date_str = email.utils.formatdate(modified_time)

            request.fields['If-Modified-Since'] = date_str

        return request


class NullWriter(BaseWriter):
    '''File writer that doesn't write files.'''
    def session(self):
        return NullWriterSession()


class NullWriterSession(BaseWriterSession):
    def process_request(self, request):
        return request

    def process_response(self, response):
        return response

    def discard_document(self, response):
        pass

    def save_document(self, response):
        pass

    def extra_resource_path(self, suffix):
        pass


class BasePathNamer(object, metaclass=abc.ABCMeta):
    '''Base class for path namers.'''
    @abc.abstractmethod
    def get_filename(self, url_info):
        '''Return the appropriate filename based on given URLInfo.'''
        pass


class PathNamer(BasePathNamer):
    '''Path namer that creates a directory hierarchy based on the URL.

    Args:
        root (str): The base path.
        index (str): The filename to use when the URL path does not indicate
            one.
        use_dir (bool): Include directories based on the URL path.
        cut (int): Number of leading directories to cut from the file path.
        protocol (bool): Include the URL scheme in the directory structure.
        hostname (bool): Include the hostname in the directory structure.

    See also: :func:`url_to_filename`, :func:`url_to_dir_path`,
    :func:`safe_filename`.
    '''
    def __init__(self, root, index='index.html', use_dir=False, cut=None,
    protocol=False, hostname=False, os_type='unix',
    no_control=True, ascii_only=True, case=None):
        self._root = root
        self._index = index
        self._cut = cut
        self._protocol = protocol
        self._hostname = hostname
        self._use_dir = use_dir
        self._os_type = os_type
        self._no_control = no_control
        self._ascii_only = ascii_only
        self._case = case

    def get_filename(self, url_info):
        url = url_info.url
        filename = url_to_filename(
            url, self._index,
            os_type=self._os_type, no_control=self._no_control,
            ascii_only=self._ascii_only, case=self._case
        )

        if self._use_dir:
            dir_path = url_to_dir_path(
                url, self._protocol, self._hostname,
                os_type=self._os_type, no_control=self._no_control,
                ascii_only=self._ascii_only, case=self._case
            )
            filename = os.path.join(dir_path, filename)

        return filename


def url_to_filename(url, index='index.html', **safe_kwargs):
    '''Return a safe filename from a URL.

    Args:
        url (str): The URL.
        index (str): If a filename could not be derived from the URL path,
            use index instead. For example, ``/images/`` will return
            ``index.html``.
        safe_kwargs: Additional arguments to :func:`safe_filename`.

    This function does not include the directories.
    '''
    assert isinstance(url, str)
    url_split_result = urllib.parse.urlsplit(url)

    filename = url_split_result.path.split('/')[-1]

    if not filename:
        filename = index

    filename = safe_filename(filename, **safe_kwargs)

    if url_split_result.query:
        if safe_kwargs.get('os_type') == 'windows':
            query_delim = '@'
        else:
            query_delim = '?'

        filename = '{0}{1}{2}'.format(
            filename, query_delim, url_split_result.query
        )

    return filename


def url_to_dir_path(url, include_protocol=False, include_hostname=False,
**safe_kwargs):
    '''Return a safe directory path from a URL.

    Args:
        url (str): The URL.
        include_protocol (bool): If True, the scheme from the URL will be
            included.
        include_hostname (bool): If True, the hostname from the URL will be
            included.
        safe_kwargs: Additional arguments to :func:`safe_filename`.

    This function does not include the filename.
    '''
    assert isinstance(url, str)
    url_split_result = urllib.parse.urlsplit(url)

    parts = []

    if include_protocol:
        parts.append(url_split_result.scheme)

    if include_hostname:
        hostname = url_split_result.hostname

        if url_split_result.port:
            if safe_kwargs.get('os_type') == 'windows':
                port_delim = '+'
            else:
                port_delim = ':'

            hostname = '{0}{1}{2}'.format(
                hostname, port_delim, url_split_result.port
            )

        parts.append(hostname)

    for path_part in url_split_result.path.split('/'):
        if path_part:
            parts.append(path_part)

    if not url.endswith('/') and parts:
        parts.pop()

    if not parts:
        return ''

    parts = [safe_filename(part, **safe_kwargs) for part in parts]
    return os.path.join(*parts)


class PercentEncoder(collections.defaultdict):
    '''Percent encoder.'''
    # The percent-encoder was inspired from urllib.parse
    def __init__(self, unix=False, control=False, windows=False, ascii_=False):
        super().__init__()
        self.unix = unix
        self.control = control
        self.windows = windows
        self.ascii = ascii_

    def __missing__(self, char):
        assert isinstance(char, bytes)

        char_num = ord(char)

        if (self.unix and char == b'/')\
        or (self.control and (0 <= char_num <= 31 or 128 <= char_num <= 159))\
        or (self.windows and char in br'\|/:?"*<>')\
        or (self.ascii and char_num > 127):
            value = b'%' + base64.b16encode(char)
        else:
            value = char

        self[char] = value
        return value

    def quote(self, bytes_string):
        quoter = self.__getitem__
        return b''.join(
            [quoter(bytes_string[i:i + 1]) for i in range(len(bytes_string))]
        )


_encoder_cache = {}


def safe_filename(filename, os_type='unix', no_control=True, ascii_only=True,
case=None, encoding='utf8'):
    '''Return a safe filename or path part.

    Args:
        filename (str): The filename or path component.
        os_type (str): If ``unix``, escape the slash. If ``windows``, escape
            extra Windows characters.
        no_control (bool): If True, escape control characters.
        ascii_only (bool): If True, escape non-ASCII characters.
        case (str): If ``lower``, lowercase the string. If ``upper``, uppercase
            the string.
        encoding (str): The character encoding.

    This function assumes that `filename` has not already been percent-encoded.

    Returns:
        str
    '''
    assert isinstance(filename, str)

    if filename in ('.', os.curdir):
        new_filename = '%2E'
    elif filename in ('.', os.pardir):
        new_filename = '%2E%2E'
    else:
        unix = os_type == 'unix'
        windows = os_type == 'windows'
        encoder_args = (unix, no_control, windows, ascii_only)

        if encoder_args not in _encoder_cache:
            _encoder_cache[encoder_args] = PercentEncoder(
                unix=unix, control=no_control, windows=windows,
                ascii_=ascii_only
            )

        encoder = _encoder_cache[encoder_args]
        encoded_filename = filename.encode(encoding)
        new_filename = encoder.quote(encoded_filename).decode(encoding)

    if os_type == 'windows':
        if new_filename[-1] in ' .':
            new_filename = '{0}{1:02X}'.format(
                new_filename[:-1], new_filename[-1]
            )

    if case == 'lower':
        new_filename = new_filename.lower()
    elif case == 'upper':
        new_filename = new_filename.upper()

    return new_filename
