# encoding=utf-8
import gettext
import logging
import tornado.gen
import toro

from wpull.database import Status, NotFound
from wpull.errors import (ExitStatus, ServerError, ConnectionRefused, DNSNotFound, 
    SSLVerficationError)
from wpull.http import NetworkError, ProtocolError
from wpull.url import URLInfo
import wpull.util


try:
    from collections import OrderedDict
except ImportError:
    from wpull.backport.collections import OrderedDict

_logger = logging.getLogger(__name__)
_ = gettext.gettext


class Engine(object):
    ERROR_CODE_MAP = OrderedDict([
        (ServerError, ExitStatus.server_error),
        (ProtocolError, ExitStatus.protocol_error),
        (SSLVerficationError, ExitStatus.ssl_verification_error),
        (DNSNotFound, ExitStatus.network_failure),
        (ConnectionRefused, ExitStatus.network_failure),
        (NetworkError, ExitStatus.network_failure),
        (OSError, ExitStatus.file_io_error),
        (IOError, ExitStatus.file_io_error),
        (ValueError, ExitStatus.parser_error),
    ])

    def __init__(self, url_table, request_client, processor, concurrent=1):
        self._url_table = url_table
        self._request_client = request_client
        self._processor = processor
        self._worker_semaphore = toro.BoundedSemaphore(concurrent)
        self._done_event = toro.Event()
        self._concurrent = concurrent
        self._num_worker_busy = 0
        self._exit_code = 0
        self._stopping = False

    @tornado.gen.coroutine
    def __call__(self):
        self._release_in_progress()
        self._run_workers()

        yield self._done_event.wait()

        self._compute_exit_code_from_stats()

        if self._exit_code == ExitStatus.ssl_verification_error:
            self._print_ssl_error()

        self._processor.close()
        self._print_stats()
        self._request_client.close()

        raise tornado.gen.Return(self._exit_code)

    def _release_in_progress(self):
        _logger.debug('Release in-progress.')
        self._url_table.release()

    @tornado.gen.coroutine
    def _run_workers(self):
        while True:
            yield self._worker_semaphore.acquire()
            self._process_input()

    def _get_next_url_record(self):
        _logger.debug('Get next URL todo.')

        try:
            url_record = self._url_table.get_and_update(
                Status.todo, new_status=Status.in_progress)
        except NotFound:
            url_record = None

        if not url_record:
            try:
                _logger.debug('Get next URL error.')
                url_record = self._url_table.get_and_update(
                    Status.error, new_status=Status.in_progress)
            except NotFound:
                url_record = None

        return url_record

    @tornado.gen.coroutine
    def _process_input(self):
        try:
            while True:
                if not self._stopping:
                    url_record = self._get_next_url_record()
                else:
                    url_record = None

                if not url_record:
                    # TODO: need better check if we are done
                    if self._num_worker_busy == 0:
                        self.stop(force=True)
                    yield wpull.util.sleep(1.0)
                else:
                    break

            self._num_worker_busy += 1

            url_info = URLInfo.parse(url_record.url)
            url_item = URLItem(self._url_table, url_info, url_record)

            yield self._process_url_item(url_item)

            assert url_item.is_processed

            _logger.debug('Table size: {0}.'.format(self._url_table.count()))
        except Exception as error:
            _logger.exception('Fatal exception.')
            self._update_exit_code_from_error(error)
            self.stop(force=True)

        self._num_worker_busy -= 1
        self._worker_semaphore.release()

    @tornado.gen.coroutine
    def _process_url_item(self, url_item):
        _logger.debug('Begin session for {0} {1}.'.format(
            url_item.url_record, url_item.url_info))

        with self._processor.session(url_item) as session:
            while True:
                if not session.should_fetch():
                    break

                should_reprocess = yield self._process_session(
                    session, url_item)

                wait_time = session.wait_time()

                if wait_time:
                    _logger.debug('Sleeping {0}.'.format(wait_time))
                    yield wpull.util.sleep(wait_time)

                if not should_reprocess:
                    break

    @tornado.gen.coroutine
    def _process_session(self, session, url_item):
        _logger.debug('Session iteration for {0} {1}'.format(
            url_item.url_record, url_item.url_info))

        request = session.new_request()

        _logger.info(_('Fetching ‘{url}’.').format(url=request.url_info.url))

        try:
            response = yield self._request_client.fetch(request,
                response_factory=session.response_factory())
        except (NetworkError, ProtocolError) as error:
            response = None
            _logger.error(
                _('Fetching ‘{url}’ encountered an error: {error}')\
                    .format(url=request.url_info.url, error=error)
            )

            is_done = session.handle_error(error)
        else:
            _logger.info(
                _('Fetched ‘{url}’: {status_code} {reason}. '
                    'Length: {content_length} [{content_type}].').format(
                    url=request.url_info.url,
                    status_code=response.status_code,
                    reason=response.status_reason,
                    content_length=response.fields.get('Content-Length'),
                    content_type=response.fields.get('Content-Type'),
                )
            )

            is_done = session.handle_response(response)

        if not is_done:
            # Retry request for things such as redirects
            raise tornado.gen.Return(True)
        else:
            self._close_instance_body(request)
            self._close_instance_body(response)

    def _close_instance_body(self, instance):
        if hasattr(instance, 'body') \
        and hasattr(instance.body, 'content_file') \
        and instance.body.content_file:
            instance.body.content_file.close()

    def stop(self, force=False):
        _logger.debug('Stopping. force={0}'.format(force))

        self._stopping = True

        if force:
            self._done_event.set()

    def _update_exit_code_from_error(self, error):
        for error_type, exit_code in self.ERROR_CODE_MAP.items():
            if isinstance(error, error_type):
                self._update_exit_code(exit_code)
                break
        else:
            self._update_exit_code(ExitStatus.generic_error)

    def _update_exit_code(self, code):
        if code:
            if self._exit_code:
                self._exit_code = min(self._exit_code, code)
            else:
                self._exit_code = code

    def _compute_exit_code_from_stats(self):
        for error_type in self._processor.statistics.errors:
            exit_code = self.ERROR_CODE_MAP.get(error_type)
            if exit_code:
                self._update_exit_code(exit_code)

    def _print_stats(self):
        stats = self._processor.statistics
        time_length = stats.stop_time - stats.start_time

        _logger.info(_('FINISHED.'))
        _logger.info(_('Time length: {time:.1f} seconds.')\
            .format(time=time_length))
        _logger.info(_('Downloaded: {num_files} files, {total_size} bytes.')\
            .format(num_files=stats.files, total_size=stats.size))
        _logger.info(_('Exiting with status {0}.').format(self._exit_code))

    def _print_ssl_error(self):
        _logger.info(_('A SSL certificate could not be verified.'))
        _logger.info(_('To ignore and proceed insecurely, '
            'use ‘--no-check-certificate’.'))


class URLItem(object):
    def __init__(self, url_table, url_info, url_record):
        self._url_table = url_table
        self._url_info = url_info
        self._url_record = url_record
        self._url = self._url_record.url
        self._processed = False
        self._try_count_incremented = False

    @property
    def url_info(self):
        return self._url_info

    @property
    def url_record(self):
        return self._url_record

    @property
    def is_processed(self):
        return self._processed

    def skip(self):
        _logger.debug(_('Skipping ‘{url}’.').format(url=self._url))
        self._url_table.update(self._url, status=Status.skipped)

        self._processed = True

    def set_status(self, status, increment_try_count=True):
        assert not self._try_count_incremented

        if increment_try_count:
            self._try_count_incremented = True

        _logger.debug('Marking URL {0} status {1}.'.format(self._url, status))
        self._url_table.update(
            self._url,
            increment_try_count=increment_try_count,
            status=status
        )

        self._processed = True

    def set_value(self, **kwargs):
        self._url_table.update(self._url, **kwargs)

    def add_inline_url_infos(self, url_infos):
        inline_urls = tuple([info.url for info in url_infos])
        _logger.debug('Adding inline URLs {0}'.format(inline_urls))
        self._url_table.add(
            inline_urls,
            inline=1,
            level=self._url_record.level + 1,
            referrer=self._url_record.url,
            top_url=self._url_record.top_url or self._url_record.url
        )

    def add_linked_url_infos(self, url_infos):
        linked_urls = tuple([info.url for info in url_infos])
        _logger.debug('Adding linked URLs {0}'.format(linked_urls))
        self._url_table.add(
            linked_urls,
            level=self._url_record.level + 1,
            referrer=self._url_record.url,
            top_url=self._url_record.top_url or self._url_record.url
        )

    def add_url_item(self, url_info, request):
        # TODO: the request should be serialized into the url_table
        raise NotImplementedError()
