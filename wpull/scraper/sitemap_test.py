import unittest

import wpull.util
from wpull.body import Body
from wpull.document.htmlparse.lxml_ import HTMLParser
from wpull.pipeline.item import LinkType
from wpull.protocol.http.request import Request, Response
from wpull.scraper.sitemap import SitemapScraper


class TestSitemap(unittest.TestCase):
    def test_sitemap_scraper_robots(self):
        scraper = SitemapScraper(HTMLParser())
        request = Request('http://example.com/robots.txt')
        response = Response(200, 'OK')
        response.body = Body()

        with wpull.util.reset_file_offset(response.body):
            response.body.write(
                b'Sitemap: http://example.com/sitemap00.xml'
            )

        scrape_result = scraper.scrape(request, response)
        inline_urls = scrape_result.inline_links
        linked_urls = scrape_result.linked_links

        self.assertEqual({
            'http://example.com/sitemap00.xml',
        },
            linked_urls
        )
        self.assertFalse(inline_urls)

    def test_sitemap_scraper_invalid_robots(self):
        scraper = SitemapScraper(HTMLParser())
        request = Request('http://example.com/robots.txt')
        response = Response(200, 'OK')
        response.body = Body()

        with wpull.util.reset_file_offset(response.body):
            response.body.write(
                b'dsfju3wrji kjasSItemapsdmjfkl wekie;er :Ads fkj3m /Dk'
            )

        scrape_result = scraper.scrape(request, response)
        inline_urls = scrape_result.inline_links
        linked_urls = scrape_result.linked_links

        self.assertFalse(linked_urls)
        self.assertFalse(inline_urls)

    def test_sitemap_scraper_xml_index(self):
        scraper = SitemapScraper(HTMLParser())
        request = Request('http://example.com/sitemap.xml')
        response = Response(200, 'OK')
        response.body = Body()

        with wpull.util.reset_file_offset(response.body):
            response.body.write(
                b'''<?xml version="1.0" encoding="UTF-8"?>
                <sitemapindex
                xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                   <sitemap>
                      <loc>http://www.example.com/sitemap1.xml.gz</loc>
                      <lastmod>2004-10-01T18:23:17+00:00</lastmod>
                   </sitemap>
                </sitemapindex>
            '''
            )

        scrape_result = scraper.scrape(request, response)
        inline_urls = scrape_result.inline_links
        linked_urls = scrape_result.linked_links

        self.assertEqual({
            'http://www.example.com/sitemap1.xml.gz',
        },
            linked_urls
        )
        self.assertFalse(inline_urls)

    def test_sitemap_scraper_xml(self):
        scraper = SitemapScraper(HTMLParser())
        request = Request('http://example.com/sitemap.xml')
        response = Response(200, 'OK')
        response.body = Body()

        with wpull.util.reset_file_offset(response.body):
            response.body.write(
                b'''<?xml version="1.0" encoding="UTF-8"?>
                <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                   <url>
                      <loc>http://www.example.com/</loc>
                      <lastmod>2005-01-01</lastmod>
                      <changefreq>monthly</changefreq>
                      <priority>0.8</priority>
                   </url>
                </urlset>
            '''
            )

        scrape_result = scraper.scrape(request, response)
        inline_urls = scrape_result.inline_links
        linked_urls = scrape_result.linked_links

        self.assertEqual({
            'http://www.example.com/',
        },
            linked_urls
        )
        self.assertFalse(inline_urls)

    def test_sitemap_scraper_invalid_xml(self):
        scraper = SitemapScraper(HTMLParser())
        request = Request('http://example.com/sitemap.xml')
        response = Response(200, 'OK')
        response.body = Body()

        with wpull.util.reset_file_offset(response.body):
            response.body.write(
                b'''<?xml version="1.0" encoding="UTF-8"?>
                <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                   <url>
                      <loc>http://www.example.com/</loc>
            '''
            )

        scrape_result = scraper.scrape(request, response)
        inline_urls = scrape_result.inline_links
        linked_urls = scrape_result.linked_links

        self.assertEqual({
            'http://www.example.com/',
        },
            linked_urls
        )
        self.assertFalse(inline_urls)

    def test_sitemap_scraper_reject_type(self):
        scraper = SitemapScraper(HTMLParser())
        request = Request('http://example.com/sitemap.xml')
        response = Response(200, 'OK')
        response.body = Body()

        with wpull.util.reset_file_offset(response.body):
            response.body.write(
                b'''<?xml version="1.0" encoding="UTF-8"?>
                <sitemapindex
                xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                   <sitemap>
                      <loc>http://www.example.com/sitemap1.xml.gz</loc>
                      <lastmod>2004-10-01T18:23:17+00:00</lastmod>
                   </sitemap>
                </sitemapindex>
            '''
            )

        scrape_result = scraper.scrape(request, response,
                                       link_type=LinkType.css)
        self.assertFalse(scrape_result)
