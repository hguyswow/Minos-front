"""Tiny local HTTP/HTTPS forward proxy for WSL (binds 127.0.0.1 only).
WSL's own TCP is blocked on this PC, so WSL tools use this proxy running on Windows.
Run:  python winproxy.py [port]   (default 3128). Stop with Ctrl+C or by killing the process.
"""
import http.client
import select
import socket
import socketserver
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3128
HOP = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers',
       'transfer-encoding', 'upgrade', 'proxy-connection'}


class H(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    def do_CONNECT(self):
        host, _, port = self.path.partition(':')
        try:
            up = socket.create_connection((host, int(port or 443)), timeout=20)
        except Exception as e:
            self.send_error(502, str(e))
            return
        self.send_response(200, 'Connection Established')
        self.end_headers()
        c = self.connection
        try:
            while True:
                r, _, _ = select.select([c, up], [], [], 60)
                if not r:
                    break
                for s in r:
                    data = s.recv(65536)
                    if not data:
                        return
                    (up if s is c else c).sendall(data)
        except Exception:
            pass
        finally:
            up.close()

    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        conn = http.client.HTTPSConnection(u.netloc, timeout=30) if u.scheme == 'https' else http.client.HTTPConnection(u.netloc, timeout=30)
        path = u.path + ('?' + u.query if u.query else '')
        hdr = {k: v for k, v in self.headers.items() if k.lower() not in HOP and k.lower() != 'host'}
        hdr['Host'] = u.netloc
        try:
            body = None
            if self.command in ('POST', 'PUT'):
                body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            conn.request(self.command, path or '/', body=body, headers=hdr)
            resp = conn.getresponse()
            data = resp.read()
        except Exception as e:
            self.send_error(502, str(e))
            return
        self.send_response(resp.status, resp.reason)
        for k, v in resp.getheaders():
            if k.lower() not in HOP and k.lower() != 'content-length':
                self.send_header(k, v)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(data)

    do_HEAD = do_POST = do_PUT = do_GET


class S(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == '__main__':
    with S(('127.0.0.1', PORT), H) as srv:
        print('proxy on 127.0.0.1:%d' % PORT, flush=True)
        srv.serve_forever()
