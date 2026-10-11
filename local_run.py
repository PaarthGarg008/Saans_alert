"""Run SaansAlert locally against moto (fake AWS on your laptop).

Usage (from the saansalert folder, next to template.yaml):
    python local_run.py ingest   -> fetch air quality data once and store it
    python local_run.py api      -> start the API at http://localhost:8000
"""
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, urlparse

# Fake AWS settings: everything goes to moto on port 5000, never to real AWS.
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["AWS_DEFAULT_REGION"] = "ap-south-1"
os.environ["AWS_ENDPOINT_URL"] = "http://localhost:5000"
os.environ.setdefault("READINGS_TABLE", "saansalert-readings")
os.environ.setdefault("STATE_TABLE", "saansalert-state")
os.environ.setdefault("TOPIC_PREFIX", "saansalert")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

ROUTES = [
    ("GET", re.compile(r"^/areas$"), "GET /areas"),
    ("GET", re.compile(r"^/areas/([^/]+)$"), "GET /areas/{areaId}"),
    ("GET", re.compile(r"^/areas/([^/]+)/history$"), "GET /areas/{areaId}/history"),
    ("POST", re.compile(r"^/subscribe$"), "POST /subscribe"),
]

CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


def run_ingest():
    from ingest.app import handler
    print(handler({}, None))


def run_api():
    from api.app import handler as api_handler

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, headers, body):
            data = body.encode("utf-8")
            self.send_response(status)
            for k, v in {**headers, **CORS}.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _handle(self):
            u = urlparse(self.path)
            for method, rx, key in ROUTES:
                m = rx.match(u.path)
                if m and method == self.command:
                    length = int(self.headers.get("Content-Length") or 0)
                    event = {
                        "routeKey": key,
                        "pathParameters": {"areaId": m.group(1)} if m.groups() else {},
                        "queryStringParameters": dict(parse_qsl(u.query)) or None,
                        "body": self.rfile.read(length).decode("utf-8") if length else "",
                        "isBase64Encoded": False,
                    }
                    r = api_handler(event, None)
                    return self._send(r["statusCode"], r.get("headers", {}), r["body"])
            self._send(404, {"Content-Type": "application/json"}, json.dumps({"error": "not found"}))

        def do_OPTIONS(self):
            self._send(204, {}, "")

        do_GET = _handle
        do_POST = _handle

    print("API running at http://localhost:8000  (try http://localhost:8000/areas)")
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "ingest":
        run_ingest()
    elif mode == "api":
        run_api()
    else:
        print("Usage: python local_run.py ingest | api")