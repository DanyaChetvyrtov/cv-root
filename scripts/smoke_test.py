#!/usr/bin/env python3
"""Verify the built UI, both Nginx proxies and actual CV inference (stdlib only)."""

import argparse
import json
import struct
import urllib.error
import urllib.request
import zlib


def blank_png(width=64, height=64):
    def chunk(kind, data):
        return (
            struct.pack("!I", len(data))
            + kind
            + data
            + struct.pack("!I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    pixels = (b"\x00" + b"\x00\x00\x00" * width) * height
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(pixels))
        + chunk(b"IEND", b"")
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web-url", default="http://127.0.0.1:5173")
    args = parser.parse_args()
    origin = args.web_url.rstrip("/")
    client = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(path, expected=200, data=None, headers=None):
        req = urllib.request.Request(origin + path, data=data, headers=headers or {})
        try:
            with client.open(req, timeout=120) as response:
                status, body = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read()
        if status != expected:
            raise SystemExit(f"FAIL {path}: expected HTTP {expected}, got {status}: {body[:500]!r}")
        print(f"PASS HTTP {status}: {path}")
        return body

    html = request("/").decode()
    if '<div id="root">' not in html or "/assets/" not in html:
        raise SystemExit("FAIL: expected the built React application")
    if request("/healthz").strip() != b"ok":
        raise SystemExit("FAIL: Nginx health endpoint")
    health = json.loads(request("/api/health"))
    if health.get("status") != "ok":
        raise SystemExit("FAIL: CV health through Nginx")
    config = json.loads(request("/auth-api/public"))
    if not config.get("issuerUri") or not config.get("browserClientId"):
        raise SystemExit("FAIL: Kotlin auth configuration through Nginx")
    for endpoint in ("me", "user", "admin"):
        request(f"/auth-api/{endpoint}", expected=401)

    boundary = "cv-lab-smoke-boundary"
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}

    def multipart(image, filename, content_type):
        return (
            f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode() + image + f"\r\n--{boundary}--\r\n".encode()

    png = multipart(blank_png(), "smoke.png", "image/png")
    result = json.loads(request("/api/vision/detect?confidence=0.25", data=png, headers=headers))
    if (result.get("width"), result.get("height")) != (64, 64):
        raise SystemExit("FAIL: inference returned incorrect image dimensions")
    if not isinstance(result.get("detections"), list) or not result.get("model"):
        raise SystemExit("FAIL: inference returned an unexpected result")
    request("/api/vision/detect?confidence=0", expected=422, data=png, headers=headers)
    request(
        "/api/vision/detect",
        expected=400,
        data=multipart(b"not an image", "invalid.txt", "text/plain"),
        headers=headers,
    )
    print("PASS built UI, API proxies, unauthenticated access and real YOLO inference")


if __name__ == "__main__":
    main()
