"""http.request —— 用 stdlib 发起 HTTP 请求，不引入 requests。"""
import json
import urllib.request

from ..core.errors import CommandFailure


class HttpRequest:
    name = "http.request"

    def run(self, args, ctx):
        url = args.get("url")
        method = (args.get("method", "GET") or "GET").upper()
        if not url:
            raise CommandFailure(self.name, "missing args.url")
        body = args.get("body")
        headers = dict(args.get("headers") or {})
        data = None
        if body is not None:
            if isinstance(body, (dict, list)):
                data = json.dumps(body).encode("utf-8")
                headers.setdefault("Content-Type", "application/json")
            else:
                data = str(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=args.get("timeout")) as resp:
                text = resp.read().decode("utf-8", errors="replace")
                try:
                    payload = json.loads(text)
                except Exception:  # noqa: BLE001
                    payload = text
                return {
                    "status": resp.status,
                    "headers": dict(resp.headers),
                    "body": payload,
                }
        except Exception as e:  # noqa: BLE001
            raise CommandFailure(self.name, f"http error: {e}")
