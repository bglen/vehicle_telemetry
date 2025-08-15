#!/usr/bin/env python3
# Minimal file server. Change ROOT to the folder you want to expose.
import http.server, socketserver, os

# serve the logs file created by install.sh in the repo directory.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(SCRIPT_DIR, "logs")
PORT = 80

if __name__ == "__main__":
    os.makedirs(ROOT, exist_ok=True)
    os.chdir(ROOT)
    with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()