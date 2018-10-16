'''Sitemap.xml'''
import gzip
import zlib

from lxml.etree import _Element as Element

from wpull.document.base import BaseExtractiveReader, BaseDocumentDetector
from wpull.document.util import is_gzip
from wpull.thirdparty import robotexclusionrulesparser
import wpull.decompression
import wpull.util


class SitemapReader(BaseDocumentDetector, BaseExtractiveReader):
    '''Sitemap XML reader.'''
    MAX_ROBOTS_FILE_SIZE = 4096

    def __init__(self, html_parser):
        super().__init__()
        self._html_parser = html_parser

    @classmethod
    def is_url(cls, url_info):
        '''Return whether the document is likely to be a Sitemap.'''
        path = url_info.path.lower()
        if path == '/robots.txt':
            return True
        if 'sitemap' in path and '.xml' in path:
            return True

    @classmethod
    def is_request(cls, request):
        '''Return whether the document is likely to be a Sitemap.'''
        return cls.is_url(request.url_info)

    @classmethod
    def is_response(cls, response):
        '''Return whether the document is likely to be a Sitemap.'''
        if response.body:
            if cls.is_file(response.body):
                return True

    @classmethod
    def is_file(cls, file):
        '''Return whether the file is likely a Sitemap.'''
        peeked_data = wpull.util.peek_file(file)

        if is_gzip(peeked_data):
            try:
                peeked_data = wpull.decompression.gzip_uncompress(
                    peeked_data, truncated=True
                )
            except zlib.error:
                pass

        peeked_data = wpull.string.printable_bytes(peeked_data)

        if b'<?xml' in peeked_data \
           and (b'<sitemapindex' in peeked_data or b'<urlset' in peeked_data):
            return True

    def iter_links(self, file, encoding=None):
        peeked_data = wpull.util.peek_file(file)

        if is_gzip(peeked_data):
            file = gzip.GzipFile(mode='rb', fileobj=file)

        if self.is_file(file):
            for html_obj in self._html_parser.parse(file, encoding):
                # Beware: some .tag values are not a str:
                # html_obj=<?xml version="1.0" encoding="UTF-8" ?>
                # tag=<cyfunction ProcessingInstruction at 0x7f17e49d78e8>
                if isinstance(html_obj, Element) and \
                   isinstance(html_obj.tag, str) and \
                   html_obj.tag.endswith('loc'):
                    if html_obj.text:
                        yield html_obj.text
        else:
            parser = robotexclusionrulesparser.RobotExclusionRulesParser()
            parser.parse(file.read(self.MAX_ROBOTS_FILE_SIZE))

            for link in parser.sitemaps:
                yield link
