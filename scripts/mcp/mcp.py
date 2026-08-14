"""Cliente MCP minimo para falar com o editor Unreal pelo servidor HTTP."""
import json
import urllib.request

URL = "http://127.0.0.1:8000/mcp"
_s = {"id": None, "rid": 0}


def rpc(method, params=None, notify=False):
    _s["rid"] += 1
    body = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        body["params"] = params
    if not notify:
        body["id"] = _s["rid"]
    headers = {"Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    if _s["id"]:
        headers["Mcp-Session-Id"] = _s["id"]
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        if not _s["id"]:
            sid = r.headers.get("Mcp-Session-Id")
            if sid:
                _s["id"] = sid
        raw = r.read().decode()
    if notify:
        return None
    for line in raw.splitlines():
        if line.startswith("data: "):
            raw = line[6:]
            break
    return json.loads(raw)


def connect():
    rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                       "clientInfo": {"name": "cli", "version": "1"}})
    rpc("notifications/initialized", notify=True)


def call(toolset, tool, args):
    res = rpc("tools/call", {"name": "call_tool",
                             "arguments": {"toolset_name": toolset,
                                           "tool_name": tool,
                                           "arguments": args}})
    return res


def result_json(res):
    """Extrai o returnValue de uma resposta de call_tool."""
    try:
        for c in res["result"]["content"]:
            if c.get("type") == "text":
                return json.loads(c["text"])
    except Exception:
        pass
    return None
