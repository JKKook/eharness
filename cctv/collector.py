"""127.0.0.1 전용 HTTP 수집기. hooks(type: http)가 보내는 JSON을 받아 bus.append 한다. 표준 라이브러리만."""
import json, os, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from . import VERSION, bus

DEFAULT_PORT = 7477
DASHBOARD = os.path.join(os.path.dirname(__file__), "view", "dashboard.html")
_cache = {"t": 0.0, "body": None, "lock": threading.Lock()}


REFRESH_SEC = 3.0


def _refresh():
    """collect()는 트랜스크립트·ps·cmux tree 를 다 읽어 부하 시 수 초 걸린다 → 백그라운드에서 주기적으로 미리 계산."""
    from .collect import collect
    t = time.time()
    rows, window, tree = collect(subagents=True)
    try:
        load1 = os.getloadavg()[0]
    except OSError:
        load1 = None
    body = json.dumps({"rows": [{**r, "tools": dict(r["tools"])} for r in rows], "window": window, "tree": tree,
                       "sys": {"load1": load1, "cores": os.cpu_count()},
                       "home": os.path.expanduser("~"), "ts": time.time(), "took_ms": round((time.time() - t) * 1000)}, ensure_ascii=False).encode()
    with _cache["lock"]:
        _cache["body"], _cache["t"] = body, time.time()


def _refresher():
    while True:
        try:
            _refresh()
        except Exception as e:                       # 한 번 실패해도 수집기는 계속 (다음 주기에 재시도)
            print(f"eharness collect: refresh failed: {e!r}", file=sys.stderr, flush=True)
        time.sleep(REFRESH_SEC)


def sessions_json():
    """항상 즉시 응답: 최근 계산 결과(≤3s 지연). 아직 첫 계산 전이면 그 자리에서 계산."""
    with _cache["lock"]:
        body = _cache["body"]
    if body is None:
        _refresh()
        with _cache["lock"]:
            body = _cache["body"]
    return body


class Handler(BaseHTTPRequestHandler):
    disable_nagle_algorithm = True        # 헤더/본문 2세그먼트 응답에 Nagle+지연ACK(~100ms)가 걸리는 것을 방지 — 훅은 동기 호출이다
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):            # 접근 로그 없음 — 이벤트 파일이 로그다
        pass

    def _send(self, code, body=b"", ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            return self._send(200, open(DASHBOARD, "rb").read(), "text/html; charset=utf-8")
        if u.path == "/favicon.ico":
            return self._send(204)
        if u.path == "/health":
            return self._send(200, json.dumps({"ok": True, "version": VERSION, "events_dir": bus.EVENTS_DIR}).encode())
        if u.path == "/api/debug":
            from .sources import terminal
            return self._send(200, json.dumps({"terminal_last": terminal.LAST, "env": {k: os.environ.get(k) for k in ("HOME", "PATH", "CMUX_SOCKET_PATH")},
                                               "uid": os.getuid(), "cwd": os.getcwd()}, ensure_ascii=False).encode())
        if u.path == "/api/manual":
            from . import manual
            return self._send(200, json.dumps(manual.load(), ensure_ascii=False).encode())
        if u.path == "/api/sessions":
            return self._send(200, sessions_json())
        if u.path == "/api/events":
            limit = int(q.get("limit", ["150"])[0]); sid = q.get("sid", [None])[0]
            since = q.get("since", [None])[0]                 # epoch 초 — 있으면 이틀치에서 필터, limit 무시
            if since:
                iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(float(since)))
                evs = [e for e in bus.read(days=2, sid=sid) if e.get("ts", "") >= iso]
            else:
                evs = list(bus.read(days=1, sid=sid))[-limit:]
            return self._send(200, json.dumps({"events": evs}, ensure_ascii=False).encode())
        self._send(404, b'{"error":"not found","routes":["/","/health","/api/sessions","/api/events"]}')

    def do_POST(self):
        n = min(int(self.headers.get("Content-Length") or 0), 1_000_000)
        try:
            data = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._send(400)
        if urlparse(self.path).path == "/api/manual":       # 수동 그룹/링크 저장 (전체 문서 교체)
            from . import manual
            out = manual.save(data if isinstance(data, dict) else {})
            with _cache["lock"]:
                _cache["t"] = 0.0                            # 다음 요청에서 즉시 재계산되도록 캐시 무효화
            try:
                _refresh()
            except Exception:
                pass
            return self._send(200, json.dumps(out, ensure_ascii=False).encode())
        if urlparse(self.path).path == "/api/session-group":  # 세션을 이름 있는 세션 그룹에 배정/해제
            from . import manual
            sid, name = str(data.get("sid") or ""), str(data.get("name") or "")[:64]
            if not sid and not name:
                return self._send(400, b'{"ok":false,"error":"sid or name required"}')
            out = manual.assign_group(sid, name, str(data.get("group") or "").strip()[:40] or None)
            with _cache["lock"]:
                _cache["t"] = 0.0
            try:
                _refresh()
            except Exception:
                pass
            return self._send(200, json.dumps({"ok": True, "manual": out}, ensure_ascii=False).encode())
        if urlparse(self.path).path == "/api/parent":       # 부모 에이전트 지정/해제 (agent → sub_agent 계층)
            from . import manual
            sid, name = str(data.get("sid") or ""), str(data.get("name") or "")[:64]
            if not sid and not name:
                return self._send(400, b'{"ok":false,"error":"sid or name required"}')
            out = manual.assign_parent(sid, name, str(data.get("parent_sid") or "") or None,
                                       str(data.get("parent_name") or "")[:64] or None)
            if out.get("error"):
                return self._send(409, json.dumps({"ok": False, "error": out["error"]}, ensure_ascii=False).encode())
            with _cache["lock"]:
                _cache["t"] = 0.0
            try:
                _refresh()
            except Exception:
                pass
            return self._send(200, json.dumps({"ok": True, "manual": out}, ensure_ascii=False).encode())
        if urlparse(self.path).path == "/api/group-move":   # 세션의 워크스페이스를 실제 cmux 사이드바 그룹으로 이동
            from .sources import terminal
            ws_id = str(data.get("ws_id") or "")
            if not ws_id:
                return self._send(400, b'{"ok":false,"error":"ws_id required"}')
            out = terminal.group_move(ws_id, group_id=str(data.get("group_id") or "") or None,
                                      new_group=str(data.get("new_group") or "").strip()[:40] or None, debug=bool(data.get("debug")))
            if out.get("ok"):
                try:
                    _refresh()                               # 사이드바 변경을 즉시 반영
                except Exception:
                    pass
            return self._send(200 if out.get("ok") else 502, json.dumps(out, ensure_ascii=False).encode())
        if data.get("hook_event_name") == "Notification" and data.get("session_id"):
            from .sources import hookstate
            hookstate.touch_notif(str(data["session_id"]))   # 메시지 상태 '입력 필요' 판정용
        bus.append(bus.to_event(data))
        self._send(200, b"{}")            # 빈 JSON = 아무 결정도 내리지 않음(관측 전용, 차단 없음)


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):   # 클라이언트가 먼저 끊은 경우(리로드)는 로그 노이즈만 → 무시
        import sys as _s
        et = _s.exc_info()[0]
        if et in (BrokenPipeError, ConnectionResetError):
            return
        super().handle_error(request, client_address)


def serve(port=DEFAULT_PORT, host="127.0.0.1"):
    bus.prune()
    threading.Thread(target=_refresher, daemon=True, name="eharness-refresh").start()
    srv = _Server((host, port), Handler)
    print(f"eharness collect: listening on http://{host}:{port}  → {bus.EVENTS_DIR}", file=sys.stderr, flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
