# encoding=utf-8
import argparse
import gettext
import logging
import os

import wpull.version


_ = gettext.gettext


class AppArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            description=_('Wget-compatible web downloader.'),
            **kwargs
        )
        self._add_app_args()

    @classmethod
    def int_0_inf(cls, string):
        if string == 'inf':
            return 0

        try:
            value = int(string)
        except ValueError as error:
            raise argparse.ArgumentTypeError(error)

        if value < 0:
            raise argparse.ArgumentTypeError(_('Value must not be negative.'))
        else:
            return value

    @classmethod
    def int_bytes(cls, string):
        if string[-1] in ('k', 'm'):
            value = cls.int_0_inf(string)
            unit = string[-1]
            if unit == 'k':
                value *= 2 ** 10
            else:
                value *= 2 ** 20
            return value
        else:
            return cls.int_0_inf(string)

    @classmethod
    def comma_list(cls, string):
        items = string.split(',')
        items = list([item.strip() for item in items])
        return items

    def _add_app_args(self):
        self.add_argument(
            'urls',
            nargs='+',
            metavar='URL',
            help=_('the URL to be downloaded'),
        )
        self._add_startup_args()
        self._add_log_and_input_args()
        self._add_download_args()
        self._add_directories_args()
        self._add_http_args()
        self._add_ssl_args()
        self._add_ftp_args()
        self._add_warc_args()
        self._add_recursive_args()
        self._add_accept_args()

    def _add_startup_args(self):
        self.add_argument(
            '-V',
            '--version',
            action='version',
            version=wpull.version.__version__
        )
#         self.add_argument(
#             '-b',
#             '--background',
#             action='store_true',
#             help=_('run as background process')
#         )
        # TODO:
#         self.add_argument(
#             '-e',
#             '--execute',
#             metavar='COMMAND',
#             action='append',
#             help=_('runs Wgetrc COMMAND'),
#         )
#         self.add_argument(
#             '--lua-script',
#             metavar='FILE',
#             type=argparse.FileType('rt'),
#             help=_('load Lua script from FILE')
#         )
        self.add_argument(
            '--database',
            metavar='FILE',
            default=':memory:',
            help=_('save database tables into FILE instead of memory'),
        )

    def _add_log_and_input_args(self):
        output_log_group = self.add_mutually_exclusive_group()
        output_log_group.add_argument(
            '-o',
            '--output-file',
            metavar='FILE',
            help=_('write program messages to FILE')
        )
        output_log_group.add_argument(
            '-a',
            '--append-output',
            metavar='FILE',
            help=_('append program messages to FILE')
        )
        verbosity_group = self.add_mutually_exclusive_group()
        verbosity_group.add_argument(
            '-d',
            '--debug',
            dest='verbosity',
            action='store_const',
            const=logging.DEBUG,
            help=_('print debugging messages')
        )
        verbosity_group.add_argument(
            '-q',
            '--quiet',
            dest='verbosity',
            action='store_const',
            const=logging.ERROR,
            help=_('do not print program messages')
        )
        verbosity_group.add_argument(
            '-v',
            '--verbose',
            dest='verbosity',
            action='store_const',
            const=logging.INFO,
            help=_('print informative program messages')
        )
        verbosity_group.add_argument(
            '-nv',
            '--no-verbose',
            dest='verbosity',
            action='store_const',
            const=logging.WARNING,
            help=_('print program warning and informative messages only')
        )
        # TODO:
#         self.add_argument(
#             '--report-speed',
#             metavar='TYPE',
#             choices=['bits'],
#         )
        self.add_argument(
            '-i',
            '--input-file',
            metavar='FILE',
            help=_('download URLs listen from FILE'),
        )
        # TODO:
#         self.add_argument(
#             '-F',
#             '--force-html',
#             action='store_true',
#             help=_('read input URL contents as HTML files')
#         )
#         self.add_argument(
#             '-B',
#             '--base',
#             metavar='URL',
#             help=_('resolves input relative URLs to URL')
#         )
#         self.add_argument(
#             '--config',
#             metavar='FILE',
#             type=argparse.FileType('rt'),
#             help=_('read configuration from FILE'),
#         )

    def _add_download_args(self):
        self.add_argument(
            '-t',
            '--tries',
            metavar='NUMBER',
            type=self.int_0_inf,
            help=_('try NUMBER of times on transient errors'),
            default=20,
        )
        self.add_argument(
            '--retry-connrefused',
            action='store_true',
            help=_('retry even if the server does not accept connections'),
        )
        self.add_argument(
            '--retry-dns-error',
            action='store_true',
            help=_('retry even if DNS fails to resolve hostname'),
        )
#         self.add_argument(
#             '-O',
#             '--output-document',
#             metavar='FILE',
#             type=argparse.FileType('w'),
#             help=_('combine and output the downloads to FILE'),
#         )
#         self.add_argument(
#             '--truncate-document',
#             action='store_true',
#             help=_('clear the output document after downloading'),
#         )
#         self.add_argument(
#             '-nc',
#             '--no-clobber',
#             action='store_true',
#             help=_('skip URLs that would overwrite files locally'),
#         )
#         self.add_argument(
#             '-c',
#             '--continue',
#             action='store_true',
#             help=_('resume downloading a partially-downloaded file'),
#         )
#         self.add_argument(
#             '--progress',
#             metavar='TYPE',
#             choices=['dot', 'bar'],
#             help=_('choose the type of progress bar'),
#         )
#         self.add_argument(
#             '-N',
#             '--timestamping',
#             action='store_true',
#             help=_('only download files that are newer than local files'),
#         )
        self.add_argument(
            '--no-use-server-timestamps',
            dest='use_server_timestamps',
            action='store_false',
            default=True,
            help=_('don’t set the last-modified time on files'),
        )
        self.add_argument(
            '-S',
            '--server-response',
            action='store_true',
            help=_('print the protocol responses from the server'),
        )
#         self.add_argument(
#             '--spider',
#             action='store_true',
#             help=_('don’t download but check if URLs exist'),
#         )
        self.add_argument(
            '-T',
            '--timeout',
            metavar='SECONDS',
            type=float,
            help=_('set all timeout options to SECONDS'),
        )
        self.add_argument(
            '--dns-timeout',
            metavar='SECS',
            type=float,
            help=_('timeout after SECS seconds for DNS requests'),
        )
        self.add_argument(
            '--connect-timeout',
            metavar='SECS',
            type=float,
            help=_('timeout after SECS seconds for connection requests'),
        )
        self.add_argument(
            '--read-timeout',
            metavar='SECS',
            type=float,
            help=_('timeout after SECS seconds for reading requests'),
        )
        self.add_argument(
            '-w',
            '--wait',
            metavar='SECONDS',
            type=float,
            default=0.0,
            help=_('wait SECONDS seconds between requests'),
        )
        self.add_argument(
            '--waitretry',
            metavar='SECONDS',
            type=float,
            default=10.0,
            help=_('wait up to SECONDS seconds on retries'),
        )
        self.add_argument(
            '--random-wait',
            action='store_true',
            help=_('randomly perturb the time between requests'),
        )
#         self.add_argument(
#             '--no-proxy',
#             action='store_true',
#             help=_('disable proxy support'),
#         )
#         self.add_argument(
#             '-Q',
#             '--quota',
#             metavar='NUMBER',
#             type=self.int_bytes,
#             help=_('stop after downloading NUMBER bytes'),
#         )
        self.add_argument(
            '--bind-address',
            metavar='ADDRESS',
            help=_('bind to ADDRESS on the local host'),
        )
#         self.add_argument(
#             '--limit-rate',
#             metavar='RATE',
#             type=self.int_bytes,
#             help=_('limit download bandwidth to RATE'),
#         )
#         self.add_argument(
#             '--no-dns-cache',
#             action='store_true',
#             help=_('disable caching of DNS lookups'),
#         )
#         self.add_argument(
#             '--rotate-dns',
#             action='store_true',
#             help=_('use different resolved IP addresses on requests'),
#         )
#         self.add_argument(
#             '--restrict-file-names',
#             metavar='OS',
#             help=_('use safe filenames for suitable OS'),
#         )
#         self.add_argument(
#             '--ignore-case',
#             action='store_true',
#             help=_('use case-insensitivity on URLs'),
#         )
        inet_group = self.add_mutually_exclusive_group()
        inet_group.add_argument(
            '-4',
            '--inet4-only',
            action='store_const',
            dest='inet_family',
            const='IPv4',
            help=_('connect to IPv4 addresses only'),
        )
        inet_group.add_argument(
            '-6',
            '--inet6-only',
            action='store_const',
            dest='inet_family',
            const='IPv6',
            help=_('connect to IPv6 addresses only'),
        )
        inet_group.add_argument(
            '--prefer-family',
            metavar='FAMILY',
            choices=['IPv6', 'IPv4'],
            help=_('prefer to connect to FAMILY IP addresses'),
        )
#         self.add_argument(
#             '--user'
#         )
#         self.add_argument(
#             '--password'
#         )
#         self.add_argument(
#             '--ask-password',
#             action='store_true',
#         )
#         self.add_argument(
#             '--no-iri',
#             action='store_true',
#         )
#         self.add_argument(
#             '--local-encoding',
#             metavar='ENC'
#         )
#         self.add_argument(
#             '--remote-encoding',
#             metavar='ENC'
#         )
#         self.add_argument(
#             '--unlink'
#         )

    def _add_directories_args(self):
        dir_group = self.add_mutually_exclusive_group()
        dir_group.add_argument(
            '-nd',
            '--no-directories',
            action='store_const',
            const='no',
            dest='use_directories',
            help=_('don’t create directories'),
        )
        dir_group.add_argument(
            '-x',
            '--force-directories',
            action='store_const',
            const='force',
            dest='use_directories',
            help=_('always create directories'),
        )
        self.add_argument(
            '-nH',
            '--no-host-directories',
            dest='host_directories',
            action='store_false',
            default=True,
            help=_('don’t create directories for hostnames')
        )
        self.add_argument(
            '--protocol-directories',
            action='store_true',
            help=_('create directories for URL schemes'),
        )
        self.add_argument(
            '-P',
            '--directory-prefix',
            metavar='PREFIX',
            default=os.curdir,
            help=_('save everything under the directory PREFIX'),
        )
        self.add_argument(
            '--cut-dirs',
            metavar='NUMBER',
            type=int,
            help=_('don’t make NUMBER of leading directories'),
        )

    def _add_http_args(self):
        # TODO:
#         self.add_argument(
#             '--http-user',
#         )
#         self.add_argument(
#             '--http-password'
#         )
#         self.add_argument(
#             '--no-cache',
#             action='store_true',
#         )
        self.add_argument(
            '--default-page',
            metavar='NAME',
            default='index.html',
            help=_('use NAME as index page if not known'),
        )
#         self.add_argument(
#             '-E',
#             '--adjust-extension',
#             action='store_true',
#         )
#         self.add_argument(
#             '--ignore-length',
#             action='store_true',
#         )
        self.add_argument(
            '--header',
            metavar='STRING',
            default=[],
            action='append',
            help=_('adds STRING to the HTTP header')
        )
        self.add_argument(
            '--max-redirect',
            metavar='NUMBER',
            type=int,
            help=_('follow only up to NUMBER document redirects'),
            default=20,
        )
#         self.add_argument(
#             '--proxy-user',
#             metavar='USER'
#         )
#         self.add_argument(
#             '--proxy-password',
#             metavar='PASS'
#         )
        self.add_argument(
            '--referer',
            metavar='URL',
            help=_('always use URL as the referrer'),
        )
        self.add_argument(
            '--save-headers',
            action='store_true',
            help=_('include server header responses in files'),
        )
        self.add_argument(
            '-U',
            '--user-agent',
            metavar='AGENT',
            help=_('use AGENT instead of Wpull’s user agent'),
        )
        self.add_argument(
            '--no-robots',
            dest='robots',
            action='store_false',
            default=True,
            help=_('ignore robots.txt directives'),
        )
#         self.add_argument(
#             '--no-http-keep-alive',
#         )
#         self.add_argument(
#             '--no-cookies'
#         )
#         self.add_argument(
#             '--load-cookies',
#             metavar='FILE'
#         )
#         self.add_argument(
#             '--save-cookies',
#             metavar='FILE'
#         )
#         self.add_argument(
#             '--keep-session-cookies'
#         )
#         self.add_argument(
#             '--post-data',
#             metavar='STRING'
#         )
#         self.add_argument(
#             '--post-file',
#             metavar='FILE'
#         )
#         self.add_argument(
#             '--method',
#             metavar='HTTPMethod',
#         )
#         self.add_argument(
#             '--body-data',
#             metavar='STRING',
#         )
#         self.add_argument(
#             '--body-file',
#             metavar='FILE'
#         )
#         self.add_argument(
#             '--content-disposition'
#         )
#         self.add_argument(
#             '--content-on-error'
#         )
#         self.add_argument(
#             '--auth-no-challenge'
#         )

    def _add_ssl_args(self):
        pass
        # TODO:
#         self.add_argument(
#             '--secure-protocol',
#             metavar='PR'
#         )
#         self.add_argument(
#             '--no-check-certificate'
#         )
#         self.add_argument(
#             '--certificate',
#             metavar='FILE'
#         )
#         self.add_argument(
#             '--certificate-type',
#             metavar='TYPE'
#         )
#         self.add_argument(
#             '--private-key',
#             metavar='FILE'
#         )
#         self.add_argument(
#             '--private-key-type',
#             metavar='TYPE'
#         )
#         self.add_argument(
#             '--ca-certificate',
#             metavar='FILE'
#         )
#         self.add_argument(
#             '--ca-directory',
#             metavar='DIR'
#         )
#         self.add_argument(
#             '--random-file',
#             metavar='FILE'
#         )
#         self.add_argument(
#             '--edg-file',
#             metavar='FILE'
#         )

    def _add_ftp_args(self):
        pass
        # TODO:
#         self.add_argument(
#             '--ftp-user',
#             metavar='USER'
#         )
#         self.add_argument(
#             '--ftp-password',
#             metavar='PASS'
#         )
#         self.add_argument(
#             '--no-remove-listing',
#             action='store_true',
#         )
#         self.add_argument(
#             '--no-glob',
#             action='store_true',
#         )
#         self.add_argument(
#             '--no-passive-ftp',
#             action='store_true',
#         )
#         self.add_argument(
#             '--preserve-permissions',
#             action='store_true',
#         )
#         self.add_argument(
#             '--retr-symlinks',
#             action='store_true',
#         )

    def _add_warc_args(self):
        self.add_argument(
            '--warc-file',
            metavar='FILENAME',
            help=_('save WARC file to filename prefixed with FILENAME'),
        )
        self.add_argument(
            '--warc-header',
            metavar='STRING',
            action='append',
            default=[],
            help=_('include STRING in WARC file metadata'),
        )
#         self.add_argument(
#             '--warc-max-size',
#             metavar='NUMBER'
#         )
#         self.add_argument(
#             '--warc-cdx'
#         )
#         self.add_argument(
#             '--warc-dedup',
#         )
        self.add_argument(
            '--no-warc-compression',
            action='store_true',
            help=_('do not compress the WARC file'),
        )
#         self.add_argument(
#             '--no-warc-digests',
#             action='store_true',
#         )
        self.add_argument(
            '--no-warc-keep-log',
            action='store_false',
            dest='warc_log',
            default=True,
            help=_('do not save a log into the WARC file'),
        )
        self.add_argument(
            '--warc-tempdir',
            metavar='DIRECTORY',
            help=_('use temporary DIRECTORY for preparing WARC files'),
        )

    def _add_recursive_args(self):
        self.add_argument(
            '-r',
            '--recursive',
            action='store_true',
            help=_('follow links and download them'),
        )
        self.add_argument(
            '-l',
            '--level',
            metavar='NUMBER',
            type=self.int_0_inf,
            default=5,
            help=_('limit recursion depth to NUMBER')
        )
        self.add_argument(
            '--delete-after',
            action='store_true',
            help=_('delete the file after downloading it'),
        )
#         self.add_argument(
#             '-k',
#             '--convert-links',
#             action='store_true',
#             help=_('make links point to local files')
#         )
#         self.add_argument(
#             '-K',
#             '--backup-converted',
#             action='store_true',
#             help=_('save original files before converting them')
#         )
#         self.add_argument(
#             '-m',
#             '--mirror',
#             action='store_true',
#             help=_('use options "-N -r -l inf --no-remove-listing"')
#         )
        self.add_argument(
            '-p',
            '--page-requisites',
            action='store_true',
            help=_('download objects embedded in pages')
        )
#         self.add_argument(
#             '--strict-comments',
#             action='store_true',
#             help=_('use strict SGML comment parsing')
#         )

    def _add_accept_args(self):
#         self.add_argument(
#             '-A',
#             '--accept',
#             metavar='LIST',
#             type=self.comma_list,
#             help=_('download only files with extension in LIST'),
#         )
#         self.add_argument(
#             '-R',
#             '--reject',
#             metavar='LIST',
#             help=_('don’t download files with extension in LIST'),
#         )
        self.add_argument(
            '--accept-regex',
            metavar='REGEX',
            help=_('download only URLs matching REGEX'),
        )
        self.add_argument(
            '--reject-regex',
            metavar='REGEX',
            help=_('don’t download URLs matching REGEX'),
        )
        self.add_argument(
            '--regex-type',
            metavar='TYPE',
            choices=['posix'],
            help=_('use regex TYPE')
        )
        self.add_argument(
            '-D',
            '--domains',
            metavar='LIST',
            type=self.comma_list,
            help=_('download only from LIST of hostname suffixes')
        )
        self.add_argument(
            '--exclude-domains',
            metavar='LIST',
            type=self.comma_list,
            help=_('don’t download from LIST of hostname suffixes')
        )
        self.add_argument(
            '--hostnames',
            metavar='LIST',
            type=self.comma_list,
            help=_('download only from LIST of hostnames')
        )
        self.add_argument(
            '--exclude-hostnames',
            metavar='LIST',
            type=self.comma_list,
            help=_('don’t download from LIST of hostnames')
        )
#         self.add_argument(
#             '--follow-ftp',
#             action='store_true',
#             help=_('follow links to FTP sites')
#         )
        self.add_argument(
            '--follow-tags',
            metavar='LIST',
            type=self.comma_list,
            help=_('follow only links contained in LIST of HTML tags'),
        )
        self.add_argument(
            '--ignore-tags',
            metavar='LIST',
            type=self.comma_list,
            help=_('don’t follow links contained in LIST of HTML tags'),
        )
        self.add_argument(
            '-H',
            '--span-hosts',
            action='store_true',
            help=_('follow links to other hostnames')
        )
        self.add_argument(
            '-L',
            '--relative',
            action='store_true',
            help=_('follow only relative links')
        )
        self.add_argument(
            '-I',
            '--include-directories',
            metavar='LIST',
            type=self.comma_list,
            help=_('download only paths in LIST')
        )
#         self.add_argument(
#             '--trust-server-names',
#             action='store_true',
#             help=_('use the last given filename by the server for filenames')
#         )
        self.add_argument(
            '-X',
            '--exclude-directories',
            metavar='LIST',
            type=self.comma_list,
            help=_('don’t download paths in LIST')
        )
        self.add_argument(
            '-np',
            '--no-parent',
            action='store_true',
            help=_('don’t follow to parent directories on URL path'),
        )
