"""
A high-speed, production ready, thread pooled, generic WSGI server.

WTFPL 2021, delinted/refactored & removed PY2 support 2021

litepresence.com <finitestate@tutamail.com>

history:
Copyright (c) 2016-2018, Florent Gallaire <f@gallai.re> <f.gallai.re/wsgiserver>
Copyright (c) 2004-2016, CherryPy Team <team@cherrypy.org>
GNU Lesser General Public License v3+

usage:
import wsgiserver
my_apps = wsgiserver.WSGIPathInfoDispatcher({'/': my_app, '/blog': my_blog_app})
server = wsgiserver.WSGIServer(my_apps, host='0.0.0.0', port=8080)
server.start()
"""

# DISABLE SELECT PYLINT TESTS
# pylint: disable=protected-access, too-few-public-methods, too-many-arguments, too-many-statements, too-many-return-statements


__version__ = "1.3"
__all__ = [
    "HTTPRequest",
    "HTTPConnection",
    "HTTPServer",
    "SizeCheckWrapper",
    "KnownLengthRFile",
    "ChunkedRFile",
    "MaxSizeExceeded",
    "NoSSLError",
    "FatalSSLAlert",
    "WorkerThread",
    "ThreadPool",
    "SSLAdapter",
    "WSGIServer",
    "Gateway",
    "WSGIGateway",
    "WSGIGatewayInterface",
    "WSGIPathInfoDispatcher",
    "SOCKET_ERRORS_TO_IGNORE",
]
import _pyio as io
import email.utils
import errno
import fcntl
import logging
import os
import queue
import re
import socket
import sys
import threading
import time
import traceback as traceback_
from urllib.parse import unquote_to_bytes, urlparse

try:
    import ssl
except ImportError as exception:
    raise ImportError("You must install SSL: github.com/openssl/openssl") from exception

if not hasattr(logging, "statistics"):
    logging.statistics = {}

ISO = "ISO-8859-1"
LF = "\n".encode(ISO)
CRLF = "\r\n".encode(ISO)
TAB = "\t".encode(ISO)
SPACE = " ".encode(ISO)
COLON = ":".encode(ISO)
SEMICOLON = ";".encode(ISO)
EMPTY = "".encode(ISO)
NUMBER_SIGN = "#".encode(ISO)
QUESTION_MARK = "?".encode(ISO)
ASTERISK = "*".encode(ISO)
FORWARD_SLASH = "/".encode(ISO)
QUOTED_SLASH = re.compile("(?i)%2F".encode(ISO))
SHUT_DOWN_REQUEST = None


def prevent_socket_inheritance(sock):
    """
    Mark the given socket fd as non-inheritable (POSIX).
    """
    file_d = sock.fileno()
    old_flags = fcntl.fcntl(file_d, fcntl.F_GETFD)
    fcntl.fcntl(file_d, fcntl.F_SETFD, old_flags | fcntl.FD_CLOEXEC)


def plat_specific_errors(*errnames):
    """
    Return error numbers for all errors in errnames on this platform.
    The 'errno' module contains different global constants depending on
    the specific platform (OS). This function will return the list of
    numeric values for a given list of potential names.
    """
    return list(dict.fromkeys([getattr(errno, k) for k in errnames if k in dir(errno)]).keys())


SOCKET_ERROR_EINTR = plat_specific_errors("EINTR", "WSAEINTR")
SOCKET_ERRORS_NONBLOCKING = plat_specific_errors("EAGAIN", "EWOULDBLOCK", "WSAEWOULDBLOCK")
SOCKET_ERRORS_TO_IGNORE = plat_specific_errors(
    "EPIPE",
    "EBADF",
    "WSAEBADF",
    "ENOTSOCK",
    "WSAENOTSOCK",
    "ETIMEDOUT",
    "WSAETIMEDOUT",
    "ECONNREFUSED",
    "WSAECONNREFUSED",
    "ECONNRESET",
    "WSAECONNRESET",
    "ECONNABORTED",
    "WSAECONNABORTED",
    "ENETRESET",
    "WSAENETRESET",
    "EHOSTDOWN",
    "EHOSTUNREACH",
    "EPROTOTYPE",
)
SOCKET_ERRORS_TO_IGNORE.append("timed out")
SOCKET_ERRORS_TO_IGNORE.append("The read operation timed out")
COMMA_SEPERATED_HEADERS = [
    header.encode(ISO)
    for header in [
        "Accept",
        "Accept-Charset",
        "Accept-Encoding",
        "Accept-Language",
        "Accept-Ranges",
        "Allow",
        "Cache-Control",
        "Connection",
        "Content-Encoding",
        "Content-Language",
        "Expect",
        "If-Match",
        "If-None-Match",
        "Pragma",
        "Proxy-Authenticate",
        "TE",
        "Trailer",
        "Transfer-Encoding",
        "Upgrade",
        "Vary",
        "Via",
        "Warning",
        "WWW-Authenticate",
    ]
]


class MaxSizeExceeded(Exception):
    """
    #
    """


class NoSSLError(Exception):
    """
    Exception raised when a client speaks HTTP to an HTTPS socket.
    """


class FatalSSLAlert(Exception):
    """
    Exception raised when the SSL implementation signals a fatal alert.
    """


class SizeCheckWrapper:
    """
    Wraps a file-like object, raising MaxSizeExceeded if too large.
    """

    def __init__(self, rfile, maxlen):
        self.rfile = rfile
        self.maxlen = maxlen
        self.bytes_read = 0

    def _check_length(self):
        """
        #
        """
        if self.maxlen and self.bytes_read > self.maxlen:
            raise MaxSizeExceeded()

    def read(self, size=None):
        """
        #
        """
        data = self.rfile.read(size)
        self.bytes_read += len(data)
        self._check_length()
        return data

    def readline(self, size=None):
        """
        #
        """
        if size is not None:
            data = self.rfile.readline(size)
            self.bytes_read += len(data)
            self._check_length()
            return data
        # User didn't specify a size ...
        # We read the line in chunks to make sure it's not a 100MB line !
        res = []
        while True:
            data = self.rfile.readline(256)
            self.bytes_read += len(data)
            self._check_length()
            res.append(data)
            # See https://github.com/cherrypy/cherrypy/issues/421
            if len(data) < 256 or data[-1:] == LF:
                return EMPTY.join(res)

    def readlines(self, sizehint=0):
        """
        #
        """
        # Shamelessly stolen from StringIO
        total = 0
        lines = []
        line = self.readline()
        while line:
            lines.append(line)
            total += len(line)
            if 0 < sizehint <= total:
                break
            line = self.readline()
        return lines

    def close(self):
        """
        #
        """
        self.rfile.close()

    def __iter__(self):
        """
        #
        """
        return self

    def __next__(self):
        """
        #
        """
        data = next(self.rfile)
        self.bytes_read += len(data)
        self._check_length()
        return data

    def next(self):
        """
        #
        """
        data = self.rfile.next()
        self.bytes_read += len(data)
        self._check_length()
        return data


class KnownLengthRFile:
    """
    Wraps a file-like object, returning an empty string when exhausted.
    """

    def __init__(self, rfile, content_length):
        self.rfile = rfile
        self.remaining = content_length

    def read(self, size=None):
        """
        #
        """
        if self.remaining == 0:
            return b""
        if size is None:
            size = self.remaining
        else:
            size = min(size, self.remaining)
        data = self.rfile.read(size)
        self.remaining -= len(data)
        return data

    def readline(self, size=None):
        """
        #
        """
        if self.remaining == 0:
            return b""
        if size is None:
            size = self.remaining
        else:
            size = min(size, self.remaining)
        data = self.rfile.readline(size)
        self.remaining -= len(data)
        return data

    def readlines(self, sizehint=0):
        """
        #
        """
        # Shamelessly stolen from StringIO
        total = 0
        lines = []
        line = self.readline(sizehint)
        while line:
            lines.append(line)
            total += len(line)
            if 0 < sizehint <= total:
                break
            line = self.readline(sizehint)
        return lines

    def close(self):
        """
        #
        """
        self.rfile.close()

    def __iter__(self):
        """
        #
        """
        return self

    def __next__(self):
        """
        #
        """
        data = next(self.rfile)
        self.remaining -= len(data)
        return data


class ChunkedRFile:
    """
    Wraps a file-like object, returning an empty string when exhausted.
    This class is intended to provide a conforming wsgi.input value for
    request entities that have been encoded with the 'chunked' transfer
    encoding.
    """

    def __init__(self, rfile, maxlen, bufsize=8192):
        self.rfile = rfile
        self.maxlen = maxlen
        self.bytes_read = 0
        self.buffer = EMPTY
        self.bufsize = bufsize
        self.closed = False

    def _fetch(self):
        """
        #
        """
        if self.closed:
            return
        line = self.rfile.readline()
        self.bytes_read += len(line)
        if self.maxlen and self.bytes_read > self.maxlen:
            raise MaxSizeExceeded("Request Entity Too Large", self.maxlen)
        line = line.strip().split(SEMICOLON, 1)
        try:
            chunk_size = line.pop(0)
            chunk_size = int(chunk_size, 16)
        except ValueError as exc:
            raise ValueError("Bad chunked transfer size: " + repr(chunk_size)) from exc
        if chunk_size <= 0:
            self.closed = True
            return
        ##            if line: chunk_extension = line[0]
        if self.maxlen and self.bytes_read + chunk_size > self.maxlen:
            raise IOError("Request Entity Too Large")
        chunk = self.rfile.read(chunk_size)
        self.bytes_read += len(chunk)
        self.buffer += chunk
        crlf = self.rfile.read(2)
        if crlf != CRLF:
            raise ValueError(
                "Bad chunked transfer coding (expected '\\r\\n', got " + repr(crlf) + ")"
            )

    def read(self, size=None):
        """
        #
        """
        data = EMPTY
        while True:
            if size and len(data) >= size:
                return data
            if not self.buffer:
                self._fetch()
                if not self.buffer:
                    # EOF
                    return data
            if size:
                remaining = size - len(data)
                data += self.buffer[:remaining]
                self.buffer = self.buffer[remaining:]
            else:
                data += self.buffer

    def readline(self, size=None):
        """
        #
        """
        data = EMPTY
        while True:
            if size and len(data) >= size:
                return data
            if not self.buffer:
                self._fetch()
                if not self.buffer:
                    # EOF
                    return data
            newline_pos = self.buffer.find(LF)
            if size:
                if newline_pos == -1:
                    remaining = size - len(data)
                    data += self.buffer[:remaining]
                    self.buffer = self.buffer[remaining:]
                else:
                    remaining = min(size - len(data), newline_pos)
                    data += self.buffer[:remaining]
                    self.buffer = self.buffer[remaining:]
            else:
                if newline_pos == -1:
                    data += self.buffer
                else:
                    data += self.buffer[:newline_pos]
                    self.buffer = self.buffer[newline_pos:]

    def readlines(self, sizehint=0):
        """
        #
        """
        # Shamelessly stolen from StringIO
        total = 0
        lines = []
        line = self.readline(sizehint)
        while line:
            lines.append(line)
            total += len(line)
            if 0 < sizehint <= total:
                break
            line = self.readline(sizehint)
        return lines

    def read_trailer_lines(self):
        """
        #
        """
        if not self.closed:
            raise ValueError("Cannot read trailers until the request body has been read.")
        while True:
            line = self.rfile.readline()
            if not line:
                # No more data--illegal end of headers
                raise ValueError("Illegal end of headers.")
            self.bytes_read += len(line)
            if self.maxlen and self.bytes_read > self.maxlen:
                raise IOError("Request Entity Too Large")
            if line == CRLF:
                # Normal end of headers
                break
            if not line.endswith(CRLF):
                raise ValueError("HTTP requires CRLF terminators")
            yield line

    def close(self):
        """
        #
        """
        self.rfile.close()


class HTTPRequest:
    """
    An HTTP Request (and response).
    A single HTTP connection may consist of multiple request/response pairs.
    """

    # The HTTPServer object which is receiving this request.
    server = None
    # The HTTPConnection object on which this request connected.
    conn = None
    # A dict of request headers.
    inheaders = {}
    # A list of header tuples to write in the response.
    outheaders = []
    # When True, the request has been parsed and is ready to begin generating
    # the response. When False, signals the calling Connection that the response
    # should not be generated and the connection should close.
    ready = False
    # Signals the calling Connection that the request should close. This does
    # not imply an error! The client and/or server may each request that the
    # connection be closed.
    close_connection = False
    # If True, output will be encoded with the chunked transfer-coding.
    # This value is set automatically inside send_headers.
    chunked_write = False

    def __init__(self, server, conn):
        self.uri = None
        self.path = None
        self.method = None
        self.query_str = None
        self.request_protocol = None
        self.server = server
        self.conn = conn
        self.ready = False
        self.started_request = False
        self.scheme = "http".encode(ISO)
        if self.server.ssl_adapter is not None:
            self.scheme = "https".encode(ISO)
        # Use the lowest-common protocol in case read_request_line errors.
        self.response_protocol = "HTTP/1.0"
        self.inheaders = {}
        self.status = ""
        self.outheaders = []
        self.sent_headers = False
        self.close_connection = self.__class__.close_connection
        self.chunked_read = False
        self.chunked_write = self.__class__.chunked_write
        self.rfile = SizeCheckWrapper(self.conn.rfile, self.server.max_request_header_size)

    def parse_request(self):
        """
        Parse the next HTTP request start-line and message-headers.
        """

        try:
            success = self.read_request_line()
        except MaxSizeExceeded:
            self.simple_response(
                "414 Request-URI Too Long",
                "The Request-URI sent with the request exceeds the maximum allowed bytes.",
            )
            return
        if not success:
            return
        try:
            success = self.read_request_headers()
        except MaxSizeExceeded:
            self.simple_response(
                "413 Request Entity Too Large",
                "The headers sent with the request exceed the maximum allowed bytes.",
            )
            return
        if not success:
            return
        self.ready = True

    def read_request_line(self):
        """
        # HTTP/1.1 connections are persistent by default. If a client
        # requests a page, then idles (leaves the connection open),
        # then rfile.readline() will raise socket.error("timed out").
        # Note that it does this based on the value given to settimeout(),
        # and doesn't need the client to request or acknowledge the close
        # (although your TCP stack might suffer for it: cf Apache's history
        # with FIN_WAIT_2).
        """
        request_line = self.rfile.readline()
        # Set started_request to True so communicate() knows to send 408
        # from here on out.
        self.started_request = True
        if not request_line:
            return False
        if request_line == CRLF:
            # RFC 2616 sec 4.1: "...if the server is reading the protocol
            # stream at the beginning of a message and receives a CRLF
            # first, it should ignore the CRLF."
            # But only ignore one leading line! else we enable a DoS.
            request_line = self.rfile.readline()
            if not request_line:
                return False
        if not request_line.endswith(CRLF):
            self.simple_response("400 Bad Request", "HTTP requires CRLF terminators")
            return False
        try:
            method, uri, req_protocol = request_line.strip().split(SPACE, 2)
            req_protocol_str = req_protocol.decode("ascii")
            int_protocol = int(req_protocol_str[5]), int(req_protocol_str[7])
        except (ValueError, IndexError):
            self.simple_response("400 Bad Request", "Malformed Request-Line")
            return False
        self.uri = uri
        self.method = method
        # uri may be an abs_path (including "http://host.domain.tld");
        # scheme, authority, path = self.parse_request_uri(uri)
        scheme, _, path = self.parse_request_uri(uri)
        if path is None:
            self.simple_response("400 Bad Request", "Invalid path in Request-URI.")
            return False
        if NUMBER_SIGN in path:
            self.simple_response("400 Bad Request", "Illegal #fragment in Request-URI.")
            return False
        if scheme:
            self.scheme = scheme
        query_str = EMPTY
        if QUESTION_MARK in path:
            path, query_str = path.split(QUESTION_MARK, 1)
        # Unquote the path+params (e.g. "/this%20path" -> "/this path").
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5.1.2
        #
        # But note that "...a URI must be separated into its components
        # before the escaped characters within those components can be
        # safely decoded." http://www.ietf.org/rfc/rfc2396.txt, sec 2.4.2
        # Therefore, "/this%2Fpath" becomes "/this%2Fpath", not "/this/path".
        try:
            atoms = [unquote_to_bytes(x) for x in QUOTED_SLASH.split(path)]
        except ValueError:
            error = sys.exc_info()[1]
            self.simple_response("400 Bad Request", error.args[0])
            return False
        path = b"%2F".join(atoms)
        self.path = path
        # Note that, like wsgiref and most other HTTP servers,
        # we "% HEX HEX"-unquote the path but not the query string.
        self.query_str = query_str
        # Compare request and server HTTP protocol versions, in case our
        # server does not support the requested protocol. Limit our output
        # to min(req, server). We want the following output:
        #     request    server     actual written   supported response
        #     protocol   protocol  response protocol    feature set
        # a     1.0        1.0           1.0                1.0
        # b     1.0        1.1           1.1                1.0
        # c     1.1        1.0           1.0                1.0
        # d     1.1        1.1           1.1                1.1
        # Notice that, in (b), the response will be "HTTP/1.1" even though
        # the client only understands 1.0. RFC 2616 10.5.6 says we should
        # only return 505 if the _major_ version is different.
        server_protocol = int(self.server.protocol[5]), int(self.server.protocol[7])
        if server_protocol[0] != int_protocol[0]:
            self.simple_response("505 HTTP Version Not Supported")
            return False
        self.request_protocol = req_protocol
        self.response_protocol = f"HTTP/{int_protocol}.{server_protocol}"
        return True

    def read_headers(self):
        """
        Read headers from the given stream into the given header dict.
        If self.inheaders is None, a new header dict is created. Returns the populated
        header dict.
        Headers which are repeated are folded together using a comma if their
        specification so dictates.
        This function raises ValueError when the read bytes violate the HTTP spec.
        You should probably return "400 Bad Request" if this happens.
        """
        if self.inheaders is None:
            self.inheaders = {}
        while True:
            line = self.rfile.readline()
            if not line:
                # No more data--illegal end of headers
                raise ValueError("Illegal end of headers.")
            if line == CRLF:
                # Normal end of headers
                break
            if not line.endswith(CRLF):
                raise ValueError("HTTP requires CRLF terminators")
            if line[0] in (SPACE, TAB):
                # It's a continuation line.
                value = line.strip()
            else:
                try:
                    key, value = line.split(COLON, 1)
                except ValueError as exc:
                    raise ValueError("Illegal header line.") from exc
                # TODO: what about TE and WWW-Authenticate?
                key = key.strip().title()
                value = value.strip()
                hname = key
            if key in COMMA_SEPERATED_HEADERS:
                existing = self.inheaders.get(hname)
                if existing:
                    value = b", ".join((existing, value))
            self.inheaders[hname] = value
        return self.inheaders

    def read_request_headers(self):
        """
        Read self.rfile into self.inheaders. Return success.
        """
        # then all the http headers
        try:
            self.read_headers()
        except ValueError:
            error = sys.exc_info()[1]
            self.simple_response("400 Bad Request", error.args[0])
            return False
        mrbs = self.server.max_request_body_size
        if mrbs and int(self.inheaders.get(b"Content-Length", 0)) > mrbs:
            self.simple_response(
                "413 Request Entity Too Large",
                "The entity sent with the request exceeds the maximum allowed bytes.",
            )
            return False
        # Persistent connection support
        if self.response_protocol == "HTTP/1.1":
            # Both server and client are HTTP/1.1
            if self.inheaders.get(b"Connection", b"") == b"close":
                self.close_connection = True
        else:
            # Either the server or client (or both) are HTTP/1.0
            if self.inheaders.get(b"Connection", b"") != b"Keep-Alive":
                self.close_connection = True
        # Transfer-Encoding support
        trans_encode = None
        if self.response_protocol == "HTTP/1.1":
            trans_encode = self.inheaders.get(b"Transfer-Encoding")
            if trans_encode:
                trans_encode = [
                    error.strip().lower() for error in trans_encode.split(b",") if error.strip()
                ]
        self.chunked_read = False
        if trans_encode:
            for enc in trans_encode:
                if enc == b"chunked":
                    self.chunked_read = True
                else:
                    # Note that, even if we see "chunked", we must reject
                    # if there is an extension we don't recognize.
                    self.simple_response("501 Unimplemented")
                    self.close_connection = True
                    return False
        # From PEP 333:
        # "Servers and gateways that implement HTTP 1.1 must provide
        # transparent support for HTTP 1.1's "expect/continue" mechanism.
        # This may be done in any of several ways:
        #   1. Respond to requests containing an Expect: 100-continue request
        #      with an immediate "100 Continue" response, and proceed normally.
        #   2. Proceed with the request normally, but provide the application
        #      with a wsgi.input stream that will send the "100 Continue"
        #      response if/when the application first attempts to read from
        #      the input stream. The read request must then remain blocked
        #      until the client responds.
        #   3. Wait until the client decides that the server does not support
        #      expect/continue, and sends the request body on its own.
        #      (This is suboptimal, and is not recommended.)
        #
        # We used to do 3, but are now doing 1. Maybe we'll do 2 someday,
        # but it seems like it would be a big slowdown for such a rare case.
        if self.inheaders.get(b"Expect", b"") == b"100-continue":
            # Don't use simple_response here, because it emits headers
            # we don't want. See
            # https://github.com/cherrypy/cherrypy/issues/951
            msg = self.server.protocol.encode("ascii")
            msg += b" 100 Continue\r\n\r\n"
            try:
                self.conn.wfile.write(msg)
            except socket.error:
                error = sys.exc_info()[1]
                if error.args[0] not in SOCKET_ERRORS_TO_IGNORE:
                    raise
        return True

    def parse_request_uri(self, uri):
        """
        Parse a Request-URI into (scheme, authority, path).
        Note that Request-URI's must be one of::
            Request-URI    = "*" | absoluteURI | abs_path | authority
        Therefore, a Request-URI which starts with a double forward-slash
        cannot be a "net_path"::
            net_path      = "//" authority [ abs_path ]
        Instead, it must be interpreted as an "abs_path" with an empty first
        path segment::
            abs_path      = "/"  path_segments
            path_segments = segment *( "/" segment )
            segment       = *pchar *( ";" param )
            param         = *pchar
        """
        if uri == ASTERISK:
            return None, None, uri
        # scheme, authority, path, params, query, fragment = urlparse(uri)
        scheme, authority, path, _, _, _ = urlparse(uri)
        if scheme and QUESTION_MARK not in scheme:
            # An absoluteURI.
            # If there's a scheme (and it must be http or https), then:
            # http_URL = "http:" "//" host [ ":" port ] [ abs_path [ "?" query
            # ]]
            return scheme, authority, path
        if uri.startswith(FORWARD_SLASH):
            # An abs_path.
            return None, None, uri
        # An authority.
        return None, uri, None

    def respond(self):
        """
        Call the gateway and write its iterable output.
        """
        mrbs = self.server.max_request_body_size
        if self.chunked_read:
            self.rfile = ChunkedRFile(self.conn.rfile, mrbs)
        else:
            content_len = int(self.inheaders.get(b"Content-Length", 0))
            if mrbs and mrbs < content_len:
                if not self.sent_headers:
                    self.simple_response(
                        "413 Request Entity Too Large",
                        "The entity sent with the request exceeds the maximum allowed bytes.",
                    )
                return
            self.rfile = KnownLengthRFile(self.conn.rfile, content_len)
        self.server.gateway(self).respond()
        if self.ready and not self.sent_headers:
            self.sent_headers = True
            self.send_headers()
        if self.chunked_write:
            self.conn.wfile.write(b"0\r\n\r\n")

    def simple_response(self, status, msg=""):
        """
        Write a simple response back to the client.
        """
        status = str(status)
        proto_status = f"{self.server.protocol} {status}\r\n"
        content_length = f"Content-Length: {len(msg)}\r\n"
        content_type = "Content-Type: text/plain\r\n"
        buf = [
            proto_status.encode(ISO),
            content_length.encode(ISO),
            content_type.encode(ISO),
        ]
        if status[:3] in ("413", "414"):
            # Request Entity Too Large / Request-URI Too Long
            self.close_connection = True
            if self.response_protocol == "HTTP/1.1":
                # This will not be true for 414, since read_request_line
                # usually raises 414 before reading the whole line, and we
                # therefore cannot know the proper response_protocol.
                buf.append(b"Connection: close\r\n")
            else:
                # HTTP/1.0 had no 413/414 status nor Connection header.
                # Emit 400 instead and trust the message body is enough.
                status = "400 Bad Request"
        buf.append(CRLF)
        if msg:
            if isinstance(msg, str):
                msg = msg.encode(ISO)
            buf.append(msg)
        try:
            self.conn.wfile.write(EMPTY.join(buf))
        except socket.error:
            error = sys.exc_info()[1]
            if error.args[0] not in SOCKET_ERRORS_TO_IGNORE:
                raise

    def write(self, chunk):
        """
        Write unbuffered data to the client.
        """
        if self.chunked_write and chunk:
            chunk_size_hex = hex(len(chunk))[2:].encode("ascii")
            buf = [chunk_size_hex, CRLF, chunk, CRLF]
            self.conn.wfile.write(EMPTY.join(buf))
        else:
            self.conn.wfile.write(chunk)

    def send_headers(self):
        """
        Assert, process, and send the HTTP response message-headers.
        You must set self.status, and self.outheaders before calling this.
        """
        hkeys = [key.lower() for key, value in self.outheaders]
        status = int(self.status[:3])
        if status == 413:
            # Request Entity Too Large. Close conn to avoid garbage.
            self.close_connection = True
        elif b"content-length" not in hkeys:
            # "All 1xx (informational), 204 (no content),
            # and 304 (not modified) responses MUST NOT
            # include a message-body." So no point chunking.
            if status < 200 or status in (204, 205, 304):
                pass
            else:
                if self.response_protocol == "HTTP/1.1" and self.method != b"HEAD":
                    # Use the chunked transfer-coding
                    self.chunked_write = True
                    self.outheaders.append((b"Transfer-Encoding", b"chunked"))
                else:
                    # Closing the conn is the only way to determine len.
                    self.close_connection = True
        if b"connection" not in hkeys:
            if self.response_protocol == "HTTP/1.1":
                # Both server and client are HTTP/1.1 or better
                if self.close_connection:
                    self.outheaders.append((b"Connection", b"close"))
            else:
                # Server and/or client are HTTP/1.0
                if not self.close_connection:
                    self.outheaders.append((b"Connection", b"Keep-Alive"))
        if (not self.close_connection) and (not self.chunked_read):
            # Read any remaining request body data on the socket.
            # "If an origin server receives a request that does not include an
            # Expect request-header field with the "100-continue" expectation,
            # the request includes a request body, and the server responds
            # with a final status code before reading the entire request body
            # from the transport connection, then the server SHOULD NOT close
            # the transport connection until it has read the entire request,
            # or until the client closes the connection. Otherwise, the client
            # might not reliably receive the response message. However, this
            # requirement is not be construed as preventing a server from
            # defending itself against denial-of-service attacks, or from
            # badly broken client implementations."
            remaining = getattr(self.rfile, "remaining", 0)
            if remaining > 0:
                self.rfile.read(remaining)
        if b"date" not in hkeys:
            self.outheaders.append(
                (
                    b"Date",
                    email.utils.formatdate(usegmt=True).encode(ISO),
                )
            )
        if b"server" not in hkeys:
            self.outheaders.append(
                (
                    b"Server",
                    self.server.server_name.encode(ISO),
                )
            )
        proto = self.server.protocol.encode("ascii")
        buf = [proto + SPACE + self.status + CRLF]
        for key, value in self.outheaders:
            buf.append(key + COLON + SPACE + value + CRLF)
        buf.append(CRLF)
        self.conn.wfile.write(EMPTY.join(buf))


class BufferedWriter(io.BufferedWriter):
    """
    Faux file object attached to a socket object.
    """

    def write_execute(self, buf):
        """
        #
        """
        self._checkClosed()
        if isinstance(buf, str):
            raise TypeError("can't write str to binary stream")
        with self._write_lock:
            self._write_buf.extend(buf)
            self._flush_unlocked()
            return len(buf)

    def write(self, b):
        self.write_execute(b)


    def _flush_unlocked(self):
        """
        #
        """
        self._checkClosed("flush of closed file")
        while self._write_buf:
            try:
                # ssl sockets only except 'bytes', not bytearrays
                # so perhaps we should conditionally wrap this for perf?
                written = self.raw.write(bytes(self._write_buf))
            except io.BlockingIOError as error:
                written = error.characters_written
            del self._write_buf[:written]


class HTTPConnection:
    """
    An HTTP connection (active socket).
    server: the Server object which received this connection.
    socket: the raw socket object (usually TCP) for this connection.
    makefile: a fileobject class for reading from the socket.
    """

    remote_addr = None
    remote_port = None
    ssl_env = None
    rbufsize = io.DEFAULT_BUFFER_SIZE
    wbufsize = io.DEFAULT_BUFFER_SIZE
    RequestHandlerClass = HTTPRequest

    def __init__(self, server, sock):
        self.server = server
        self.socket = sock
        self.rfile = io.BufferedReader(socket.SocketIO(sock, "rb"), self.rbufsize)
        self.wfile = BufferedWriter(socket.SocketIO(sock, "wb"), self.wbufsize)
        self.requests_seen = 0

    def communicate(self):
        """
        Read each request and respond appropriately.
        """
        request_seen = False
        try:
            while True:
                # (re)set req to None so that if something goes wrong in
                # the RequestHandlerClass constructor, the error doesn't
                # get written to the previous request.
                req = None
                req = self.RequestHandlerClass(self.server, self)
                # This order of operations should guarantee correct pipelining.
                req.parse_request()
                if self.server.stats["Enabled"]:
                    self.requests_seen += 1
                if not req.ready:
                    # Something went wrong in the parsing (and the server has
                    # probably already made a simple_response). Return and
                    # let the conn close.
                    return
                request_seen = True
                req.respond()
                if req.close_connection:
                    return
        except socket.error:
            error = sys.exc_info()[1]
            errnum = error.args[0]
            # sadly SSL sockets return a different (longer) time out string
            if errnum in ["timed out", "The read operation timed out"]:
                # Don't error if we're between requests; only error
                # if 1) no request has been started at all, or 2) we're
                # in the middle of a request.
                # See https://github.com/cherrypy/cherrypy/issues/853
                if (not request_seen) or (req and req.started_request):
                    # Don't bother writing the 408 if the response
                    # has already started being written.
                    if req and not req.sent_headers:
                        try:
                            req.simple_response("408 Request Timeout")
                        except FatalSSLAlert:
                            # Close the connection.
                            return
            elif errnum not in SOCKET_ERRORS_TO_IGNORE:
                self.server.error_log(
                    f"socket.error {repr(errnum)}",
                    traceback=True,
                )
                if req and not req.sent_headers:
                    try:
                        req.simple_response("500 Internal Server Error")
                    except FatalSSLAlert:
                        # Close the connection.
                        return
            return
        except (KeyboardInterrupt, SystemExit):
            print("Keyboard Interrupt")
            raise
        except FatalSSLAlert:
            # Close the connection.
            return
        except NoSSLError:
            if req and not req.sent_headers:
                # Unwrap our wfile
                self.wfile = BufferedWriter(socket.SocketIO(self.socket._sock, "wb"), self.wbufsize)

                req.simple_response(
                    "400 Bad Request",
                    "The client sent a plain HTTP request, but "
                    "this server only speaks HTTPS on this port.",
                )
                self.linger = True
        except Exception:
            error = sys.exc_info()[1]
            self.server.error_log(repr(error), traceback=True)
            if req and not req.sent_headers:
                try:
                    req.simple_response("500 Internal Server Error")
                except FatalSSLAlert:
                    # Close the connection.
                    return

    linger = False

    def close(self):
        """
        Close the socket underlying this connection.
        """
        self.rfile.close()
        if not self.linger:
            self.socket.close()
        else:
            # On the other hand, sometimes we want to hang around for a bit
            # to make sure the client has a chance to read our entire
            # response. Skipping the close() calls here delays the FIN
            # packet until the socket object is garbage-collected later.
            # Someday, perhaps, we'll do the full lingering_close that
            # Apache does, but not today.
            pass


class TrueyZero:
    """
    An object which equals and does math like the integer 0 but evals True.
    """

    def __add__(self, other):
        return other

    def __radd__(self, other):
        return other


class WorkerThread(threading.Thread):
    """
    Thread which continuously polls a Queue for Connection objects.
    Due to the timing issues of polling a Queue, a WorkerThread does not
    check its own 'ready' flag after it has started. To stop the thread,
    it is necessary to stick a SHUT_DOWN_REQUEST object onto the Queue
    (one for each running WorkerThread).
    """

    # The current connection pulled off the Queue, or None.
    conn = None
    # The HTTP Server which spawned this thread, and which owns the
    # Queue and is placing active connections into it.
    server = None
    # A simple flag for the calling server to know when this thread
    # has begun polling the Queue.

    ready = False

    def __init__(self, server):
        self.ready = False
        self.server = server
        self.requests_seen = 0
        self.bytes_read = 0
        self.bytes_written = 0
        self.start_time = None
        self.work_time = 0
        self.stats = {
            "Requests": lambda s: self.requests_seen + (
                (self.start_time is None) and TrueyZero() or self.conn.requests_seen
            ),
            "Bytes Read": lambda s: self.bytes_read + (
                (self.start_time is None) and TrueyZero() or self.conn.rfile.bytes_read
            ),
            "Bytes Written": lambda s: self.bytes_written + (
                (self.start_time is None) and TrueyZero() or self.conn.wfile.bytes_written
            ),
            "Work Time": lambda s: self.work_time + (
                (self.start_time is None) and TrueyZero() or time.time() - self.start_time
            ),
            "Read Throughput": lambda s: s["Bytes Read"](s) / (s["Work Time"](s) or 1e-6),
            "Write Throughput": lambda s: s["Bytes Written"](s) / (s["Work Time"](s) or 1e-6),
        }
        threading.Thread.__init__(self)

    def run(self):
        """
        #
        """
        self.server.stats["Worker Threads"][self.getName()] = self.stats
        try:
            self.ready = True
            while True:
                conn = self.server.requests.get()
                if conn is SHUT_DOWN_REQUEST:
                    return
                self.conn = conn
                if self.server.stats["Enabled"]:
                    self.start_time = time.time()
                try:
                    conn.communicate()
                finally:
                    conn.close()
                    if self.server.stats["Enabled"]:
                        self.requests_seen += self.conn.requests_seen
                        self.bytes_read += self.conn.rfile.bytes_read
                        self.bytes_written += self.conn.wfile.bytes_written
                        self.work_time += time.time() - self.start_time
                        self.start_time = None
                    self.conn = None
        except (KeyboardInterrupt, SystemExit):
            error = sys.exc_info()[1]
            self.server.interrupt = error


class ThreadPool:
    """
    A Request Queue for an HTTPServer which pools threads.
    ThreadPool objects must provide min, get(), put(obj), start()
    and stop(timeout) attributes.
    """

    def __init__(
        self,
        server,
        min_threads=10,
        max_threads=-1,
        accepted_queue_size=-1,
        accepted_queue_timeout=10,
    ):
        self.server = server
        self.min_threads = min_threads
        self.max_threads = max_threads
        self._threads = []
        self._queue = queue.Queue(maxsize=accepted_queue_size)
        self._queue_put_timeout = accepted_queue_timeout
        self.get = self._queue.get

    def start(self):
        """
        Start the pool of threads.
        """
        for _ in range(self.min_threads):
            self._threads.append(WorkerThread(self.server))
        for worker in self._threads:
            worker.setName("CP Server " + worker.getName())
            worker.start()
            # SLEEP?
        for worker in self._threads:
            while not worker.ready:
                time.sleep(0.1)

    def _get_idle(self):
        """
        Number of worker threads which are idle. Read-only.
        """
        return len([t for t in self._threads if t.conn is None])

    idle = property(_get_idle, doc=_get_idle.__doc__)

    def put(self, obj):
        """
        #
        """
        self._queue.put(obj, block=True, timeout=self._queue_put_timeout)
        if obj is SHUT_DOWN_REQUEST:
            return

    def grow(self, amount):
        """
        Spawn new worker threads (not above self.max).
        """
        if self.max_threads > 0:
            budget = max(self.max_threads - len(self._threads), 0)
        else:
            # self.max <= 0 indicates no maximum
            budget = float("inf")
        n_new = min(amount, budget)
        workers = [self._spawn_worker() for i in range(n_new)]
        while not all(worker.ready for worker in workers):
            time.sleep(0.1)
        self._threads.extend(workers)

    def _spawn_worker(self):
        """
        #
        """
        worker = WorkerThread(self.server)
        worker.setName("CP Server " + worker.getName())
        # SLEEP?
        worker.start()
        return worker

    def shrink(self, amount):
        """
        Kill off worker threads (not below self.min).
        """
        # Grow/shrink the pool if necessary.
        # Remove any dead threads from our list
        for thread in self._threads:
            if not thread.isAlive():
                self._threads.remove(thread)
                amount -= 1
        # calculate the number of threads above the minimum
        n_extra = max(len(self._threads) - self.min_threads, 0)
        # don'thread remove more than amount
        n_to_remove = min(amount, n_extra)
        # put shutdown requests on the queue equal to the number of threads
        # to remove. As each request is processed by a worker, that worker
        # will terminate and be culled from the list.
        for _ in range(n_to_remove):
            self._queue.put(SHUT_DOWN_REQUEST)

    def stop(self, timeout=5):
        """
        # Must shut down threads here so the code that calls
        # this method can know when all threads are stopped.
        """
        for worker in self._threads:
            self._queue.put(SHUT_DOWN_REQUEST)
        # Don't join currentThread (when stop is called inside a request).
        current = threading.currentThread()
        if timeout and timeout >= 0:
            endtime = time.time() + timeout
        while self._threads:
            worker = self._threads.pop()
            if worker is not current and worker.isAlive():
                try:
                    if timeout is None or timeout < 0:
                        worker.join()
                    else:
                        remaining_time = endtime - time.time()
                        if remaining_time > 0:
                            worker.join(remaining_time)
                        if worker.isAlive():
                            # We exhausted the timeout.
                            # Forcibly shut down the socket.
                            connection = worker.conn
                            if connection and not connection.rfile.closed:
                                try:
                                    connection.socket.shutdown(socket.SHUT_RD)
                                except TypeError:
                                    # pyOpenSSL sockets don't take an arg
                                    connection.socket.shutdown()
                            worker.join()
                # Ignore repeated Ctrl-C.
                # See
                # https://github.com/cherrypy/cherrypy/issues/691.
                except (AssertionError, KeyboardInterrupt):
                    pass

    def _get_qsize(self):
        return self._queue.qsize()

    qsize = property(_get_qsize)


class SSLAdapter:
    """
    A wrapper for integrating Python's builtin ssl module with WSGIServer.
    """

    # The filename of the server SSL certificate.
    certificate = None
    # The filename of the server's private key file.
    private_key = None
    # The filename of the certificate chain file.
    # The ssl.SSLContext that will be used to wrap sockets where available
    # (on Python > 2.7.9 / 3.3)
    certificate_chain = None

    context = None

    def __init__(self, certfile, keyfile, ca_certs=None):
        if ssl is None:
            raise ImportError("You must install the ssl module to use HTTPS.")
        self.certificate = certfile
        self.private_key = keyfile
        self.certificate_chain = ca_certs
        if hasattr(ssl, "create_default_context"):
            self.context = ssl.create_default_context(
                purpose=ssl.Purpose.CLIENT_AUTH, cafile=self.certificate_chain
            )
            self.context.load_cert_chain(self.certificate, self.private_key)

    def bind(self, sock):
        """
        Wrap and return the given socket.
        """
        return sock

    def wrap(self, sock):
        """
        Wrap and return the given socket, plus WSGI environ entries.
        """
        try:
            if self.context is not None:
                sock = self.context.wrap_socket(
                    sock, do_handshake_on_connect=True, server_side=True
                )
            else:
                sock = ssl.wrap_socket(
                    sock,
                    do_handshake_on_connect=True,
                    server_side=True,
                    certfile=self.certificate,
                    keyfile=self.private_key,
                    ssl_version=ssl.PROTOCOL_SSLv23,
                    ca_certs=self.certificate_chain,
                )
        except ssl.SSLError as exc:
            error = sys.exc_info()[1]
            if error.errno == ssl.SSL_ERROR_EOF:
                # This is almost certainly due to the cherrypy engine
                # 'pinging' the socket to assert it'sock connectable;
                # the 'ping' isn't SSL.
                return None, {}
            if error.errno == ssl.SSL_ERROR_SSL:
                if "http request" in error.args[1].lower():
                    # The client is speaking HTTP to an HTTPS server.
                    raise NoSSLError from exc
                if "unknown protocol" in error.args[1].lower():
                    # The client is speaking some non-HTTP protocol.
                    # Drop the conn.
                    return None, {}
            raise
        return sock, self.get_environ(sock)

    # TODO: fill this out more with mod ssl env
    def get_environ(self, sock):
        """
        Create WSGI environ entries to be merged into each request.
        """
        cipher = sock.cipher()
        # SSL_VERSION_INTERFACE 	string 	The mod_ssl program version
        # SSL_VERSION_LIBRARY 	string 	The OpenSSL program version
        ssl_environ = {
            "wsgi.url_scheme": "https",
            "HTTPS": "on",
            "SSL_PROTOCOL": cipher[1],
            "SSL_CIPHER": cipher[0],
        }
        return ssl_environ

    def makefile(self, sock, mode="r", bufsize=io.DEFAULT_BUFFER_SIZE):
        """
        #
        """
        return io.BufferedReader(socket.SocketIO(sock, mode), bufsize)


class HTTPServer:
    """
    An HTTP server.
    """

    _bind_addr = "127.0.0.1"
    _interrupt = None

    # A Gateway instance
    gateway = None
    # The minimum number of worker threads to create (default 10)
    min_threads = None
    # The maximum number of worker threads to create (default -1 = no limit).
    max_threads = None
    # The name of the server; defaults to socket.gethostname()
    server_name = None
    # The version string to write in the Status-Line of all HTTP responses.
    # For example, "HTTP/1.1" is the default. This also limits the supported
    # features used in the response
    protocol = "HTTP/1.1"
    # The 'backlog' arg to socket.listen(); max queued connections
    request_queue_size = 5  # (default 5).
    # The total time, in seconds, to wait for worker threads to cleanly exit.
    shutdown_timeout = 5
    # The timeout in seconds for accepted connections (default 10)
    timeout = 10
    # A version string for the HTTPServer
    version = "WSGIserver/" + __version__
    # The value to set for the SERVER_SOFTWARE entry in the WSGI environ.
    # If None, this defaults to ``'%s Server' % self.version``
    software = None
    # An internal flag which marks whether the socket is accepting
    # connections.
    ready = False
    # The maximum size, in bytes, for request headers, or 0 for no limit
    max_request_header_size = 0
    # The maximum size, in bytes, for request bodies, or 0 for no limit
    max_request_body_size = 0
    # If True (the default since 3.1), sets the TCP_NODELAY socket option
    nodelay = True
    # The class to use for handling HTTP connections
    ConnectionClass = HTTPConnection
    # An instance of SSLAdapter (or a subclass).
    # You must have the corresponding SSL driver library installed
    ssl_adapter = None

    def __init__(self, bind_addr, gateway, min_threads=10, max_threads=-1, server_name=None):
        self.bind_addr = bind_addr
        self.gateway = gateway
        self.requests = ThreadPool(self, min_threads=min_threads or 1, max_threads=max_threads)
        if not server_name:
            server_name = socket.gethostname()
        self.server_name = server_name
        self.clear_stats()
        self._start_time = None
        self.socket = None

    def clear_stats(self):
        """
        #
        """
        self._start_time = None
        self._run_time = 0
        self.stats = {
            "Enabled": False,
            "Bind Address": lambda s: repr(self.bind_addr),
            "Run time": lambda s: (not s["Enabled"]) and -1 or self.runtime(),
            "Accepts": 0,
            "Accepts/sec": lambda s: s["Accepts"] / self.runtime(),
            "Queue": lambda s: getattr(self.requests, "qsize", None),
            "Threads": lambda s: len(getattr(self.requests, "_threads", [])),
            "Threads Idle": lambda s: getattr(self.requests, "idle", None),
            "Socket Errors": 0,
            "Requests": (
                lambda s: (not s["Enabled"])
                and -1
                or sum([w["Requests"](w) for w in s["Worker Threads"].values()], 0)
            ),
            "Bytes Read": (
                lambda s: (not s["Enabled"])
                and -1
                or sum([w["Bytes Read"](w) for w in s["Worker Threads"].values()], 0)
            ),
            "Bytes Written": (
                lambda s: (not s["Enabled"])
                and -1
                or sum([w["Bytes Written"](w) for w in s["Worker Threads"].values()], 0)
            ),
            "Work Time": (
                lambda s: (not s["Enabled"])
                and -1
                or sum([w["Work Time"](w) for w in s["Worker Threads"].values()], 0)
            ),
            "Read Throughput": (
                lambda s: (not s["Enabled"])
                and -1
                or sum(
                    [
                        w["Bytes Read"](w) / (w["Work Time"](w) or 1e-6)
                        for w in s["Worker Threads"].values()
                    ],
                    0,
                )
            ),
            "Write Throughput": (
                lambda s: (not s["Enabled"])
                and -1
                or sum(
                    [
                        w["Bytes Written"](w) / (w["Work Time"](w) or 1e-6)
                        for w in s["Worker Threads"].values()
                    ],
                    0,
                )
            ),
            "Worker Threads": {},
        }
        logging.statistics[f"WSGIserver {id(self)}"] = self.stats

    def runtime(self):
        """
        #
        """
        if self._start_time is None:
            ret = self._run_time
        else:
            ret = self._run_time + (time.time() - self._start_time)
        return ret

    def __str__(self):
        """
        #
        """
        return f"{self.__module__}.{self.__class__.__name__}({self.bind_addr!r})"

    def _get_bind_addr(self):
        """
        #
        """
        return self._bind_addr

    def _set_bind_addr(self, value):
        """
        #
        """
        if isinstance(value, tuple) and value[0] in ("", None):
            # Despite the socket module docs, using '' does not
            # allow AI_PASSIVE to work. Passing None instead
            # returns '0.0.0.0' like we want. In other words:
            #     host    AI_PASSIVE     result
            #      ''         Y         192.168.x.y
            #      ''         N         192.168.x.y
            #     None        Y         0.0.0.0
            #     None        N         127.0.0.1
            # But since you can get the same effect with an explicit
            # '0.0.0.0', we deny both the empty string and None as values.
            raise ValueError(
                "Host values of '' or None are not allowed. "
                "Use '0.0.0.0' (IPv4) or '::' (IPv6) instead "
                "to listen on all active interfaces."
            )
        self._bind_addr = value

    bind_addr = property(
        _get_bind_addr,
        _set_bind_addr,
        doc="""The interface on which to listen for connections.
        For TCP sockets, a (host, port) tuple. Host values may be any IPv4
        or IPv6 address, or any valid hostname. The string 'localhost' is a
        synonym for '127.0.0.1' (or '::1', if your hosts file prefers IPv6).
        The string '0.0.0.0' is a special IPv4 entry meaning "any active
        interface" (INADDR_ANY), and '::' is the similar IN6ADDR_ANY for
        IPv6. The empty string or None are not allowed.
        For UNIX sockets, supply the filename as a string.
        Systemd socket activation is automatic and doesn't require tempering
        with this variable""",
    )

    def start(self):
        """
        Run the server forever.
        """
        self._interrupt = None
        if self.software is None:
            self.software = f"{self.version} Server"
        # Select the appropriate socket
        self.socket = None
        if os.getenv("LISTEN_PID", None):
            # systemd socket activation
            self.socket = socket.fromfd(3, socket.AF_INET, socket.SOCK_STREAM)
        elif isinstance(self.bind_addr, (str,)):
            # AF_UNIX socket
            # So we can reuse the socket...
            try:
                os.unlink(self.bind_addr)
            except:
                pass
            # So everyone can access the socket...
            try:
                os.chmod(self.bind_addr, 0o777)
            except:
                pass
            info = [(socket.AF_UNIX, socket.SOCK_STREAM, 0, "", self.bind_addr)]
        else:
            # AF_INET or AF_INET6 socket
            # Get the correct address family for our host (allows IPv6
            # addresses)
            host, port = self.bind_addr
            try:
                info = socket.getaddrinfo(
                    host,
                    port,
                    socket.AF_UNSPEC,
                    socket.SOCK_STREAM,
                    0,
                    socket.AI_PASSIVE,
                )
            except socket.gaierror:
                if ":" in self.bind_addr[0]:
                    info = [
                        (
                            socket.AF_INET6,
                            socket.SOCK_STREAM,
                            0,
                            "",
                            self.bind_addr + (0, 0),
                        )
                    ]
                else:
                    info = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", self.bind_addr)]
        if not self.socket:
            msg = "No socket could be created"
            for res in info:
                family, socktype, proto, _, _sa = res
                try:
                    self.bind(family, socktype, proto)
                    break
                except socket.error as error:
                    msg = f"{msg} -- ({_sa}: {error})"
                    if self.socket:
                        self.socket.close()
                    self.socket = None
            if not self.socket:
                raise socket.error(msg)
        # Timeout so KeyboardInterrupt can be caught on Win32
        self.socket.settimeout(1)
        self.socket.listen(self.request_queue_size)
        # Create worker threads
        self.requests.start()
        self.ready = True
        self._start_time = time.time()
        while self.ready:
            try:
                self.tick()
            except (KeyboardInterrupt, SystemExit):
                self.stop()
            except:
                self.error_log("Error in HTTPServer.tick", traceback=True)
            if self.interrupt:
                while self.interrupt is True:
                    # Wait for self.stop() to complete. See _set_interrupt.
                    time.sleep(0.1)
                if self.interrupt:
                    raise self.interrupt

    def error_log(self, msg="", traceback=False):
        """
        Override this in subclasses as desired
        """
        sys.stderr.write(msg + "\n")
        sys.stderr.flush()
        if traceback:
            tblines = traceback_.format_exc()
            sys.stderr.write(tblines)
            sys.stderr.flush()

    def bind(self, family, socktype, proto=0):
        """
        Create (or recreate) the actual socket object.
        """
        self.socket = socket.socket(family, socktype, proto)
        prevent_socket_inheritance(self.socket)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if self.nodelay and not isinstance(self.bind_addr, str):
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        if self.ssl_adapter is not None:
            self.socket = self.ssl_adapter.bind(self.socket)
        # If listening on the IPV6 any address ('::' = IN6ADDR_ANY),
        # activate dual-stack. See
        # https://github.com/cherrypy/cherrypy/issues/871.
        if (
            hasattr(socket, "AF_INET6")
            and family == socket.AF_INET6
            and self.bind_addr[0] in ("::", "::0", "::0.0.0.0")
        ):
            try:
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            except (AttributeError, socket.error):
                # Apparently, the socket option is not available in
                # this machine's TCP stack
                pass
        self.socket.bind(self.bind_addr)

    def tick(self):
        """
        Accept a new connection and put it on the Queue.
        """
        try:
            sock, addr = self.socket.accept()
            if self.stats["Enabled"]:
                self.stats["Accepts"] += 1
            if self.ready:
                return
            prevent_socket_inheritance(sock)
            if hasattr(sock, "settimeout"):
                sock.settimeout(self.timeout)
            ssl_env = {}
            # if ssl cert and key are set, we try to be a secure HTTP server
            if self.ssl_adapter is not None:
                try:
                    sock, ssl_env = self.ssl_adapter.wrap(sock)
                except NoSSLError:
                    msg = (
                        "The client sent a plain HTTP request, but "
                        "this server only speaks HTTPS on this port."
                    )
                    buf = [
                        f"{self.protocol} 400 Bad Request\r\n",
                        f"Content-Length: {len(msg)}\r\n",
                        "Content-Type: text/plain\r\n\r\n",
                        msg,
                    ]
                    sock_to_make = sock
                    wfile = self.ssl_adapter.makefile(sock_to_make, "wb", io.DEFAULT_BUFFER_SIZE)

                    wfile = BufferedWriter(socket.SocketIO(sock, "wb"), io.DEFAULT_BUFFER_SIZE)
                    try:
                        wfile.write(("".join(buf)).encode(ISO))
                    except socket.error:
                        error = sys.exc_info()[1]
                        if error.args[0] not in SOCKET_ERRORS_TO_IGNORE:
                            raise
                    return
                if not sock:
                    return
                # Re-apply our timeout since we may have a new socket object
                if hasattr(sock, "settimeout"):
                    sock.settimeout(self.timeout)
            conn = self.ConnectionClass(self, sock)
            if not isinstance(self.bind_addr, (str,)):
                # optional values
                # Until we do DNS lookups, omit REMOTE_HOST
                if addr is None:  # sometimes this can happen
                    # figure out if AF_INET or AF_INET6.
                    if len(sock.getsockname()) == 2:
                        # AF_INET
                        addr = ("0.0.0.0", 0)
                    else:
                        # AF_INET6
                        addr = ("::", 0)
                conn.remote_addr = addr[0]
                conn.remote_port = addr[1]
            conn.ssl_env = ssl_env
            try:
                self.requests.put(conn)
            except queue.Full:
                # Just drop the conn. TODO: write 503 back?
                conn.close()
                return
        except socket.timeout:
            # The only reason for the timeout in start() is so we can
            # notice keyboard interrupts on Win32, which don't interrupt
            # accept() by default
            return
        except socket.error:
            sys_exc = sys.exc_info()[1]
            if self.stats["Enabled"]:
                self.stats["Socket Errors"] += 1
            if sys_exc.args[0] in SOCKET_ERROR_EINTR:
                # I *think* this is right. EINTR should occur when a signal
                # is received during the accept() call; all docs say retry
                # the call, and I *think* I'm reading it right that Python
                # will then go ahead and poll for and handle the signal
                # elsewhere. See
                # https://github.com/cherrypy/cherrypy/issues/707.
                return
            if sys_exc.args[0] in SOCKET_ERRORS_NONBLOCKING:
                # Just try again. See
                # https://github.com/cherrypy/cherrypy/issues/479.
                return
            if sys_exc.args[0] in SOCKET_ERRORS_TO_IGNORE:
                # Our socket was closed.
                # See https://github.com/cherrypy/cherrypy/issues/686.
                return
            raise

    def _get_interrupt(self):
        """
        #
        """
        return self._interrupt

    def _set_interrupt(self, interrupt):
        """
        #
        """
        self._interrupt = True
        self.stop()
        self._interrupt = interrupt

    interrupt = property(
        _get_interrupt,
        _set_interrupt,
        doc="Set this to an Exception instance to interrupt the server.",
    )

    def stop(self):
        """
        Gracefully shutdown a server that is serving forever.
        """
        self.ready = False
        if self._start_time is not None:
            self._run_time += time.time() - self._start_time
        self._start_time = None
        sock = getattr(self, "socket", None)
        if sock:
            if not isinstance(self.bind_addr, (str,)):
                # Touch our own socket to make accept() return immediately.
                try:
                    host, port = sock.getsockname()[:2]
                except socket.error:
                    error = sys.exc_info()[1]
                    if error.args[0] not in SOCKET_ERRORS_TO_IGNORE:
                        # Changed to use error code and not message
                        # See
                        # https://github.com/cherrypy/cherrypy/issues/860.
                        raise
                else:
                    # Note that we're explicitly NOT using AI_PASSIVE,
                    # here, because we want an actual IP to touch.
                    # localhost won't work if we've bound to a public IP,
                    # but it will if we bound to '0.0.0.0' (INADDR_ANY).
                    for res in socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM):
                        _af, socktype, proto, _, _sa = res
                        sock = None
                        try:
                            sock = socket.socket(_af, socktype, proto)
                            # See
                            # http://groups.google.com/group/cherrypy-users/
                            #     browse_frm/thread/bbfe5eb39c904fe0
                            sock.settimeout(1.0)
                            sock.connect((host, port))
                            sock.close()
                        except socket.error:
                            if sock:
                                sock.close()
            if hasattr(sock, "close"):
                sock.close()
            self.socket = None
        self.requests.stop(self.shutdown_timeout)


class Gateway:
    """
    A base class to interface HTTPServer with other systems, such as WSGI.
    """

    def __init__(self, req):
        self.req = req

    def respond(self):
        """
        Process the current request. Must be overridden in a subclass.
        """
        raise NotImplementedError


class WSGIServer(HTTPServer):
    """
    A subclass of HTTPServer which calls a WSGI application.
    """

    def __init__(
        self,
        wsgi_app,
        host="0.0.0.0",
        port=8080,
        num_threads=10,
        server_name=None,
        max_threads=-1,
        request_queue_size=5,
        timeout=10,
        shutdown_timeout=5,
        accepted_queue_size=-1,
        accepted_queue_timeout=10,
        certfile=None,
        keyfile=None,
        ca_certs=None,
    ):
        self.requests = ThreadPool(
            self,
            min_threads=num_threads or 1,
            max_threads=max_threads,
            accepted_queue_size=accepted_queue_size,
            accepted_queue_timeout=accepted_queue_timeout,
        )
        self.wsgi_app = wsgi_app
        self.gateway = WSGIGatewayInterface
        self.bind_addr = (host, port)
        if not server_name:
            server_name = socket.gethostname()
        self.server_name = server_name
        self.request_queue_size = request_queue_size
        self.timeout = timeout
        self.shutdown_timeout = shutdown_timeout
        self.clear_stats()
        if certfile and keyfile:
            self.ssl_adapter = SSLAdapter(certfile, keyfile, ca_certs)

    def _get_numthreads(self):
        """
        #
        """
        return self.requests.min_threads

    def _set_numthreads(self, value):
        """
        #
        """
        self.requests.min_threads = value

    numthreads = property(_get_numthreads, _set_numthreads)


class WSGIGateway(Gateway):
    """
    A base class to interface HTTPServer with WSGI.
    """

    def __init__(self, req):
        self.req = req
        self.started_response = False
        self.env = self.get_environ()
        self.remaining_bytes_out = None

    def get_environ(self):
        """
        Return a new environ dict targeting the given wsgi.version
        """
        raise NotImplementedError

    def respond(self):
        """
        Process the current request.
        """
        response = self.req.server.wsgi_app(self.env, self.start_response)
        try:
            for chunk in response:
                # "The start_response callable must not actually transmit
                # the response headers. Instead, it must store them for the
                # server or gateway to transmit only after the first
                # iteration of the application return value that yields
                # a NON-EMPTY string, or upon the application's first
                # invocation of the write() callable." (PEP 333)
                if chunk:
                    if not isinstance(chunk, bytes):
                        raise ValueError("WSGI Applications must yield bytes")
                    self.write(chunk)
        finally:
            if hasattr(response, "close"):
                response.close()

    def start_response(self, status, headers, exc_info=None):
        """
        WSGI callable to begin the HTTP response.
        """
        # "The application may call start_response more than once,
        # if and only if the exc_info argument is provided."
        if self.started_response and not exc_info:
            raise AssertionError("WSGI start_response called a second time with no exc_info.")
        self.started_response = True
        # "if exc_info is provided, and the HTTP headers have already been
        # sent, start_response must raise an error, and should raise the
        # exc_info tuple."
        if self.req.sent_headers:
            try:
                raise exc_info[0](exc_info[1]).with_traceback(exc_info[2])
            finally:
                exc_info = None
        self.req.status = self._encode_status(status)
        for key, header in headers:
            if not isinstance(key, str):
                raise TypeError(f"WSGI response header key {key!r} is not of type str.")
            if not isinstance(header, str):
                raise TypeError(f"WSGI response header value {header!r} is not of type str.")
            if key.lower() == "content-length":
                self.remaining_bytes_out = int(header)
            out_header = key.encode(ISO), header.encode(ISO)
            self.req.outheaders.append(out_header)
        return self.write

    @staticmethod
    def _encode_status(status):
        """
        According to PEP 3333, when using Python 3, the response status
        and headers must be bytes masquerading as unicode; that is, they
        must be of type "str" but are restricted to code points in the
        "latin-1" set.
        """
        if not isinstance(status, str):
            raise TypeError("WSGI response status is not of type str.")
        return status.encode(ISO)

    def write(self, chunk):
        """
        WSGI callable to write unbuffered data to the client.
        This method is also used internally by start_response (to write
        data from the iterable returned by the WSGI application).
        """
        if not self.started_response:
            raise AssertionError("WSGI write called before start_response.")
        chunklen = len(chunk)
        rbo = self.remaining_bytes_out
        if rbo is not None and chunklen > rbo:
            if not self.req.sent_headers:
                # Whew. We can send a 500 to the client.
                self.req.simple_response(
                    "500 Internal Server Error",
                    "The requested resource returned more bytes than the declared Content-Length.",
                )
            else:
                # Dang. We have probably already sent data. Truncate the chunk
                # to fit (so the client doesn't hang) and raise an error later.
                chunk = chunk[:rbo]
        if not self.req.sent_headers:
            self.req.sent_headers = True
            self.req.send_headers()
        self.req.write(chunk)
        if rbo is not None:
            rbo -= chunklen
            if rbo < 0:
                raise ValueError("Response body exceeds the declared Content-Length.")


class WSGIGatewayInterface(WSGIGateway):
    """
    A Gateway class to interface HTTPServer with WSGI 1.0.x.
    """

    def get_environ(self):
        """
        Return a new environ dict targeting the given wsgi.version
        """
        req = self.req
        env = {
            # set a non-standard environ entry so the WSGI app can know what
            # the *real* server protocol is (and what features to support).
            # See http://www.faqs.org/rfcs/rfc2145.html.
            "ACTUAL_SERVER_PROTOCOL": req.server.protocol,
            "PATH_INFO": (req.path).decode(ISO),
            "QUERY_STRING": (req.query_str).decode(ISO),
            "REMOTE_ADDR": req.conn.remote_addr or "",
            "REMOTE_PORT": str(req.conn.remote_port or ""),
            "REQUEST_METHOD": (req.method).decode(ISO),
            "REQUEST_URI": (req.uri).decode(ISO),
            "SCRIPT_NAME": "",
            "SERVER_NAME": req.server.server_name,
            # Bah. "SERVER_PROTOCOL" is actually the REQUEST protocol.
            "SERVER_PROTOCOL": (req.request_protocol).decode(ISO),
            "SERVER_SOFTWARE": req.server.software,
            "wsgi.errors": sys.stderr,
            "wsgi.input": req.rfile,
            "wsgi.multiprocess": False,
            "wsgi.multithread": True,
            "wsgi.run_once": False,
            "wsgi.url_scheme": (req.scheme).decode(ISO),
            "wsgi.version": (1, 0),
        }
        if isinstance(req.server.bind_addr, (str,)):
            # AF_UNIX. This isn't really allowed by WSGI, which doesn't
            # address unix domain sockets. But it's better than nothing.
            env["SERVER_PORT"] = ""
        else:
            env["SERVER_PORT"] = str(req.server.bind_addr[1])
        # Request headers
        env.update(
            ("HTTP_" + ((k).decode(ISO)).upper().replace("-", "_"), v.decode(ISO))
            for k, v in req.inheaders.items()
        )
        # CONTENT_TYPE/CONTENT_LENGTH
        content_type = env.pop("HTTP_CONTENT_TYPE", None)
        if content_type is not None:
            env["CONTENT_TYPE"] = content_type
        content_length = env.pop("HTTP_CONTENT_LENGTH", None)
        if content_length is not None:
            env["CONTENT_LENGTH"] = content_length
        if req.conn.ssl_env:
            env.update(req.conn.ssl_env)
        return env


class WSGIPathInfoDispatcher:
    """
    A WSGI dispatcher for dispatch based on the PATH_INFO.
    apps: a dict or list of (path_prefix, app) pairs.
    """

    def __init__(self, apps):
        try:
            apps = list(apps.items())
        except AttributeError:
            pass
        # Sort the apps by len(path), descending
        apps.sort(key=lambda app: len(app[0]), reverse=True)
        # The path_prefix strings must start, but not end, with a slash.
        # Use "" instead of "/".
        self.apps = [(p.rstrip("/"), a) for p, a in apps]

    def __call__(self, environ, start_response):
        """
        #
        """
        path = environ["PATH_INFO"] or "/"
        for app_path, app in self.apps:
            # The apps list should be sorted by length, descending.
            if path.startswith(app_path + "/") or path == app_path:
                environ = environ.copy()
                environ["SCRIPT_NAME"] = environ["SCRIPT_NAME"] + app_path
                environ["PATH_INFO"] = path[len(app_path) :]
                return app(environ, start_response)
        start_response("404 Not Found", [("Content-Type", "text/plain"), ("Content-Length", "0")])
        return [""]
