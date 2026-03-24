"""
serve.py — reliable local file server for Windows
Usage: python serve.py <directory> [port]
Always cd's into the directory first, then serves. Prints the URL when ready.
"""
import sys
import os
import http.server
import socketserver

directory = sys.argv[1] if len(sys.argv) > 1 else "."
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8900

os.chdir(directory)

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # silent

with socketserver.TCPServer(("", port), Handler) as httpd:
    print(f"READY http://localhost:{port}/", flush=True)
    httpd.serve_forever()
