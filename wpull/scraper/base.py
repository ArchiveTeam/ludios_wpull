'''Base classes'''
import abc
import io
from dataclasses import dataclass
from wpull.document.base import BaseTextStreamReader, \
    BaseHTMLReader, BaseExtractiveReader
from wpull.scraper.util import urljoin_safe
from wpull.pipeline.item import LinkType
from wpull.document.html import HTMLReadElement


@dataclass
class LinkInfo:
    element: HTMLReadElement
    tag: str
    attrib: str | None
    link: str
    inline: bool
    linked: bool
    base_link: str | None
    value_type: str

    link_type: LinkType

    def __hash__(self):
        return self.link.__hash__()

'''Information about a link in a lxml document.  Comparable on link only.

Attributes:
    element: An instance of :class:`.document.HTMLReadElement`.
    tag (str): The element tag name.
    attrib (str, None): If ``str``, the name of the attribute. Otherwise,
        the link was found in ``element.text``.
    link (str): The link found.
    inline (bool): Whether the link is an embedded object (like images or
        stylesheets).
    linked (bool): Whether the link is a link to another page.
    base_link (str, None): The base URL.
    value_type (str): Indicates how the link was found. Possible values are

        * ``plain``: The link was found plainly in an attribute value.
        * ``list``: The link was found in a space separated list.
        * ``css``: The link was found in a CSS text.
        * ``refresh``: The link was found in a refresh meta string.
        * ``script``: The link was found in JavaScript text.
        * ``srcset``: The link was found in a ``srcset`` attribute.

    link_type: A value from :class:`item.LinkType`.
'''


@dataclass(frozen=True)
class LinkContext:
    link: str
    inline: bool = False
    linked: bool = False
    link_type: LinkType = None
    extra: LinkInfo = None

'''A named tuple describing a scraped link.

Attributes:
    link (str): The link that was scraped.
    inline (bool): Whether the link is an embeded object.
    linked (bool): Whether the link links to another page.
    link_type: A value from :class:`.item.LinkType`.
    extra: Any extra info.
'''


class ScrapeResult(dict):
    '''Links scraped from a document.

    This class is subclassed from ``dict`` and contains convenience methods.
    '''
    def __init__(self, link_contexts, encoding):
        super().__init__()
        self.link_contexts = link_contexts
        self.encoding = encoding

    @property
    def link_contexts(self):
        '''Link Contexts.'''
        return self['link_contexts']

    @link_contexts.setter
    def link_contexts(self, value):
        self['link_contexts'] = value

    @property
    def encoding(self):
        '''Character encoding of the document.'''
        return self['encoding']

    @encoding.setter
    def encoding(self, value):
        self['encoding'] = value

    @property
    def inline_links(self):
        '''URLs of objects embedded in the document.'''
        return frozenset(context.link for context in self['link_contexts'] if context.inline)

    @property
    def linked_links(self):
        '''URLs of objects linked from the document'''
        return frozenset(context.link for context in self['link_contexts'] if context.linked)

    @property
    def inline(self):
        '''Link Context of objects embedded in the document.'''
        return frozenset(context for context in self['link_contexts'] if context.inline)

    @property
    def linked(self):
        '''Link Context of objects linked from the document'''
        return frozenset(context for context in self['link_contexts'] if context.linked)


class BaseScraper(object):
    '''Base class for scrapers.'''
    @abc.abstractmethod
    def scrape(self, request, response, link_type=None):
        '''Extract the URLs from the document.

        Args:
            request (:class:`.http.request.Request`): The request.
            response (:class:`.http.request.Response`): The response.
            link_type: A value from :class:`.item.LinkType`.

        Returns:
            ScrapeResult, None: LinkContexts and document information.

            If None, then the scraper does not support scraping the document.
        '''


class BaseTextStreamScraper(BaseScraper, BaseTextStreamReader):
    '''Base class for scrapers that process either link and non-link text.'''
    def iter_processed_text(self, file, encoding=None, base_url=None):
        '''Return the file text and processed absolute links.

        Args:
            file: A file object containing the document.
            encoding (str): The encoding of the document.
            base_url (str): The URL at which the document is located.

        Returns:
            iterator: Each item is a tuple:

            1. str: The text
            2. bool: Whether the text a link
        '''
        for text, is_link in self.iter_text(file, encoding):
            if is_link and base_url:
                new_link = urljoin_safe(base_url, text, allow_fragments=False)

                if new_link:
                    yield (new_link, is_link)
                else:
                    yield (new_link, False)
            else:
                yield (text, is_link)

    def iter_processed_links(self, file, encoding=None, base_url=None, context=False):
        '''Return the links.

        This function is a convenience function for calling
        :meth:`iter_processed_text` and returning only the links.
        '''
        if context:
            return [item for item in self.iter_processed_text(file, encoding, base_url) if item[1]]
        else:
            return [item[0] for item in self.iter_processed_text(file, encoding, base_url) if item[1]]

    def scrape_links(self, text, context=False):
        '''Convenience function for scraping from a text string.'''
        return self.iter_processed_links(io.StringIO(text), context=context)


class BaseExtractiveScraper(BaseScraper, BaseExtractiveReader):
    def iter_processed_links(self, file, encoding=None, base_url=None):
        '''Return the links.

        Returns:
            iterator: Each item is a str which represents a link.
        '''
        for link in self.iter_links(file, encoding):
            new_link = urljoin_safe(base_url, link, allow_fragments=False)
            if new_link:
                yield new_link


class BaseHTMLScraper(BaseScraper, BaseHTMLReader):
    pass


class DemuxDocumentScraper(BaseScraper):
    '''Puts multiple Document Scrapers into one.'''
    def __init__(self, document_scrapers):
        self._document_scrapers = document_scrapers

    def scrape(self, request, response, link_type=None):
        '''Iterate the scrapers, returning the first of the results.'''
        for scraper in self._document_scrapers:
            scrape_result = scraper.scrape(request, response, link_type)

            if scrape_result is None:
                continue

            if scrape_result.link_contexts:
                return scrape_result

    def scrape_info(self, request, response, link_type=None):
        '''Iterate the scrapers and return a dict of results.

        Returns:
            dict: A dict where the keys are the scrapers instances and the
            values are the results. That is, a mapping from
            :class:`BaseDocumentScraper` to :class:`ScrapeResult`.
        '''
        info = {}
        for scraper in self._document_scrapers:
            scrape_result = scraper.scrape(request, response, link_type)
            info[scraper] = scrape_result

        return info
