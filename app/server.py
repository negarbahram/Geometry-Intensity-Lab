"""Local experiment interface: python app/server.py [--port 8765]  ->  http://127.0.0.1:8765

Standard library HTTP server. Intensity processing runs in the C++ core (intensity_lab.engine); this server only passes
settings to it, draws its results and adds the detector comparison. Binds to 127.0.0.1 only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import time
import traceback
import uuid
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from intensity_lab import detector, engine, experiment, plots  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
OUTPUTS = ROOT / "outputs"
RUNS: "OrderedDict[str, dict]" = OrderedDict()     # run id -> {"result", "images", "figures"}
LOCK = threading.Lock()


def config() -> dict:
    """Datasets, defaults and engine status. When the C++ core is missing the interface shows why and cannot run."""
    info = {"engine": experiment.engine_info(), "engine_available": engine.available(), "engine_error": None,
            "detector_available": detector.available(), "saved": saved_runs(), "datasets": {}, "defaults": None}
    try:
        info["defaults"] = engine.defaults()
        info["datasets"] = {d: engine.list_images(d) for d in engine.DATASETS}
    except engine.EngineError as e:
        info["engine_available"], info["engine_error"] = False, str(e)
    return info


def do_run(settings: dict) -> dict:
    r = experiment.run(settings)
    rid = uuid.uuid4().hex[:12]
    entry = {"result": r, "images": experiment.images(r, display=True), "figures": experiment.figures(r), "png": {}}
    with LOCK:
        RUNS[rid] = entry
        while len(RUNS) > 6:
            RUNS.popitem(last=False)
    return {"run_id": rid, "summary": experiment.summary(r), "images": sorted(entry["images"]),
            "figures": sorted(entry["figures"]), "settings": r.settings}


def image_png(rid: str, name: str) -> bytes | None:
    with LOCK:
        e = RUNS.get(rid)
    if e is None:
        return None
    if name in e["figures"]:
        return e["figures"][name]
    if name not in e["images"]:
        return None
    if name not in e["png"]:
        e["png"][name] = plots.png_from_array(e["images"][name])
    return e["png"][name]


def do_save(rid: str, label: str) -> str:
    with LOCK:
        e = RUNS.get(rid)
    if e is None:
        raise KeyError("run expired: run it again before saving")
    r = e["result"]
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(r.settings["image"]).stem)[:40]
    tag = re.sub(r"[^A-Za-z0-9_-]+", "_", label)[:40]
    name = f"{time.strftime('%Y%m%d-%H%M%S')}_{r.settings['dataset'] or 'file'}_{stem}" + (f"_{tag}" if tag else "")
    return str(experiment.save(r, OUTPUTS / name))


def saved_runs() -> list[str]:
    if not OUTPUTS.exists():
        return []
    return sorted((p.name for p in OUTPUTS.iterdir() if (p / "settings.json").exists()), reverse=True)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.command, self.path.split("?")[0]))

    def _send(self, code, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, default=float).encode(), "application/json")

    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            if path in ("/", "/index.html"):
                return self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
            if path == "/api/config":
                return self._json(config())
            m = re.fullmatch(r"/api/image/([0-9a-f]+)/([a-z_]+)\.png", path)
            if m:
                png = image_png(m.group(1), m.group(2))
                return self._send(200, png, "image/png") if png else self._json({"error": "not found"}, 404)
            m = re.fullmatch(r"/api/saved/([A-Za-z0-9_.()-]+)/settings", path)
            if m and m.group(1) in saved_runs():
                return self._json(json.loads((OUTPUTS / m.group(1) / "settings.json").read_text()))
            return self._json({"error": "not found"}, 404)
        except Exception as e:
            traceback.print_exc()
            return self._json({"error": str(e)}, 500)

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if path == "/api/run":
                try:
                    return self._json(do_run(body["settings"]))
                except engine.EngineError as e:                 # no fallback: say what failed
                    return self._json({"error": str(e), "engine_error": True}, 500)
            if path == "/api/save":
                return self._json({"saved_to": do_save(body["run_id"], body.get("label", "")), "saved": saved_runs()})
            return self._json({"error": "not found"}, 404)
        except Exception as e:
            traceback.print_exc()
            return self._json({"error": f"{type(e).__name__}: {e}"}, 400)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"Geometry Intensity Lab: http://127.0.0.1:{a.port}  (Ctrl+C to stop)")
    print(f"Processing engine: {engine.NAME} at {engine.CLI}" + ("" if engine.available() else "  -- NOT BUILT"))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
