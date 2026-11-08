#!/usr/bin/env python3
"""
mock_mcp_server.py — Minimal In-Repo Stdio MCP Server for Offline Testing
========================================================================
Implements basic JSON-RPC 2.0 loop over stdio.
Used strictly for offline unit/integration testing of loader lifecycle and gating.
Never downloads or runs third-party code.
"""

import json
import sys
import time


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        req_id = req.get("id")
        method = req.get("method")

        if method == "initialize":
            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "mock-mcp-server", "version": "1.0.0"},
                },
            }
        elif method == "tools/list":
            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "echo",
                            "description": "Echo back arguments",
                            "inputSchema": {"type": "object"},
                        },
                        {
                            "name": "sleep",
                            "description": "Sleep for duration to test timeouts",
                            "inputSchema": {"type": "object"},
                        },
                    ]
                },
            }
        elif method == "tools/call":
            params = req.get("params") or {}
            tool_name = params.get("name")
            tool_args = params.get("arguments") or {}

            if tool_name == "sleep":
                dur = float(tool_args.get("seconds", 1))
                time.sleep(dur)
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": f"Slept {dur}s"}]},
                }
            else:
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": f"Echo: {json.dumps(tool_args)}"}
                        ]
                    },
                }
        else:
            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"status": "ok"},
            }

        sys.stdout.write(json.dumps(res) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
