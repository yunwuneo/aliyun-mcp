"""Launcher for alibabacloud-mcp-server.

Why this exists:
1. alibabacloud-mcp-server calls FastMCP("alibabacloud-mcp-server") without a
   host/port, and mcp 1.30's FastMCP hardcodes 127.0.0.1:8000 (its Settings env
   prefix is not honoured by that constructor), so the listen address cannot be
   changed with environment variables alone.
2. Behind nginx the public Host header is aliyun-mcp.neo7.cn, which FastMCP's
   DNS-rebinding guard rejects as "Invalid Host header" unless it is allowed.
"""

import os
import sys

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

_orig_init = FastMCP.__init__


def _patched_init(self, *args, **kwargs):
    kwargs.setdefault("host", os.environ.get("MCP_HOST", "127.0.0.1"))
    kwargs.setdefault("port", int(os.environ.get("MCP_PORT", "18070")))
    kwargs.setdefault(
        "transport_security",
        TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[
                h.strip()
                for h in os.environ.get(
                    "MCP_ALLOWED_HOSTS",
                    "aliyun-mcp.neo7.cn,127.0.0.1:18070,localhost:18070",
                ).split(",")
                if h.strip()
            ],
            allowed_origins=[
                o.strip()
                for o in os.environ.get(
                    "MCP_ALLOWED_ORIGINS",
                    "https://aliyun-mcp.neo7.cn",
                ).split(",")
                if o.strip()
            ],
        ),
    )
    _orig_init(self, *args, **kwargs)


FastMCP.__init__ = _patched_init

# The package forwards RegionId=None literally, producing ecs.none.aliyuncs.com.
# Fill in a default region whenever the caller does not supply a usable one.
import alibabacloud_mcp_server.server as _srv  # noqa: E402

_orig_create_client = _srv.create_client


def _create_client(service, region_id=None):
    if not region_id or str(region_id).lower() in ("none", "null", ""):
        region_id = os.environ.get("MCP_DEFAULT_REGION", "cn-hangzhou")
    return _orig_create_client(service, region_id)


_srv.create_client = _create_client

from alibabacloud_mcp_server.server import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
