"""SaansAlert single-process server for Railway (or any host).

Runs a fake AWS (moto) in memory, refreshes the air quality data every
2 hours, and serves the API and the website from ONE address.

Needs these environment variables:
    OPENWEATHER_API_KEY, OPENAQ_API_KEY
Railway sets PORT by itself.
"""
import json
import logging
import mimetypes
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, unquote, urlparse

MOTO_PORT = int(os.environ.get("MOTO_PORT", "5055"))

# Fake AWS: everything goes to moto inside this process, never to real AWS.
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["AWS_DEFAULT_REGION"] = "ap-south-1"
os.environ["AWS_ENDPOINT_URL"] = f"http://127.0.0.1:{MOTO_PORT}"
os.environ.setdefault("READINGS_TABLE", "saansalert-readings")
os.environ.setdefault("STATE_TABLE", "saansalert-state")
os.environ.setdefault("TOPIC_PREFIX", "saansalert")

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.realpath(os.path.join(ROOT, "frontend"))
sys.path.insert(0, os.path.join(ROOT, "backend"))

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("server")
API_LOCK = threading.Lock()
INGEST_EVERY_S = 2 * 3600

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


def start_fake_aws():
    import boto3
    from moto.server import ThreadedMotoServer
    ThreadedMotoServer(ip_address="127.0.0.1", port=MOTO_PORT, verbose=False).start()
    ddb = boto3.client("dynamodb")
    specs = [
        (os.environ["READINGS_TABLE"],
         [("areaId", "S"), ("ts", "N")], [("areaId", "HASH"), ("ts", "RANGE")]),
        (os.environ["STATE_TABLE"], [("areaId", "S")], [("areaId", "HASH")]),
    ]
    for name, attrs, keys in specs:
        for attempt in range(15):
            try:
                ddb.create_table(
                    TableName=name,
                    AttributeDefinitions=[{"AttributeName": a, "AttributeType": t} for a, t in attrs],
                    KeySchema=[{"AttributeName": a, "KeyType": k} for a, k in keys],
                    BillingMode="PAY_PER_REQUEST")
                break
            except Exception as e:
                if attempt == 14:
                    raise
                log.info("waiting for fake AWS (%s)", e)
                time.sleep(1)
    log.info("fake AWS ready")


def ingest_loop():
    from ingest.app import handler
    while True:
        try:
            log.info("ingest result: %s", handler({}, None))
        except Exception:
            log.exception("ingest failed")
        time.sleep(INGEST_EVERY_S)


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, headers, body):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(status)
        for k, v in {**headers, **CORS}.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _static(self, path):
        if path == "/config.js":  # the website talks to the same address it was loaded from
            return self._send(200, {"Content-Type": "application/javascript", "Cache-Control": "no-store"},
                              "window.CONFIG = { API_URL: window.location.origin };")
        rel = "index.html" if path in ("", "/") else unquote(path).lstrip("/")
        full = os.path.realpath(os.path.join(FRONTEND, rel))
        if not full.startswith(FRONTEND + os.sep) or not os.path.isfile(full):
            return self._send(404, {"Content-Type": "text/plain"}, "not found")
        with open(full, "rb") as f:
            body = f.read()
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        self._send(200, {"Content-Type": ctype}, body)

    def _handle(self):
        from api.app import handler as api_handler
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
                with API_LOCK:
                    r = api_handler(event, None)
                return self._send(r["statusCode"], r.get("headers", {}), r["body"])
        if self.command == "GET":
            return self._static(u.path)
        self._send(404, {"Content-Type": "application/json"}, json.dumps({"error": "not found"}))

    def do_OPTIONS(self):
        self._send(204, {}, "")

    do_GET = _handle
    do_POST = _handle


if __name__ == "__main__":
    for var in ("OPENWEATHER_API_KEY", "OPENAQ_API_KEY"):
        if not os.getenv(var):
            log.warning("%s is not set - ingest will fail", var)
    start_fake_aws()
    threading.Thread(target=ingest_loop, daemon=True).start()
    port = int(os.environ.get("PORT", "8080"))
    log.info("serving on port %s", port)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()