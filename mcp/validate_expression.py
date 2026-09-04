#!/usr/bin/env python3
"""
Local MCP server for alpha expression validation.

Tools:
- validate_expression
- validate_expression_batch
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from mcp.server.mcpserver import MCPServer

WQB_ROOT = Path(__file__).resolve().parents[1]
if str(WQB_ROOT) not in sys.path:
    sys.path.insert(0, str(WQB_ROOT))

from wqb.tools.expr.api import default_expression_validate  # noqa: E402

mcp = MCPServer("local-validate-expression")

_session = None
_logger: logging.Logger | None = None


def _get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        from wqb.api import wqb_logger

        _logger = wqb_logger(name="wqb-mcp")
    return _logger


def _brain_credentials() -> tuple[str, str] | None:
    email = (
        os.environ.get("BRAIN_EMAIL")
        or os.environ.get("BRAIN_USERNAME")
        or os.environ.get("BRAIN_CREDENTIAL_EMAIL")
    )
    password = os.environ.get("BRAIN_PASSWORD") or os.environ.get(
        "BRAIN_CREDENTIAL_PASSWORD"
    )
    if email and password:
        return email.strip(), password.strip()
    return None


def _get_session():
    global _session
    if _session is not None:
        return _session
    creds = _brain_credentials()
    if creds is None:
        raise ValueError(
            "字段校验需要 BRAIN 凭证，请设置 BRAIN_EMAIL 与 BRAIN_PASSWORD 环境变量"
        )
    from wqb.api import WQBSession

    logger = _get_logger()
    logger.info("MCP validate_expression: creating WQBSession")
    _session = WQBSession(creds, logger=logger)
    _session.auth_request(log="")
    logger.info("MCP validate_expression: auth_request complete")
    return _session


@mcp.tool()
def validate_expression_tool(expression: str) -> Dict[str, Any]:
    """
    验证单个 Alpha 表达式（词法、语法、语义，并通过 BRAIN API 校验字段）。

    Args:
        expression: Alpha 表达式文本。
    """
    logger = _get_logger()
    logger.info("validate_expression_tool: start (%d chars)", len(expression))
    session = _get_session()
    result = default_expression_validate.validate_expression(
        expression,
        check_fields=True,
        session=session,
    )
    logger.info(
        "validate_expression_tool: done is_valid=%s errors=%d",
        result.is_valid,
        len(result.errors),
    )
    return {"is_valid": result.is_valid, "errors": list(result.errors)}


@mcp.tool()
def validate_expression_batch_tool(expressions: List[str]) -> Dict[str, Any]:
    """
    批量验证 Alpha 表达式（词法、语法、语义，并通过 BRAIN API 校验字段）。

    Args:
        expressions: 表达式列表。
    """
    logger = _get_logger()
    logger.info("validate_expression_batch_tool: start count=%d", len(expressions))
    session = _get_session()
    results = default_expression_validate.validate_expression_batch(
        expressions,
        check_fields=True,
        session=session,
    )
    logger.info(
        "validate_expression_batch_tool: done valid=%d/%d",
        sum(1 for item in results if item.is_valid),
        len(results),
    )
    return {
        "results": [
            {"is_valid": item.is_valid, "errors": list(item.errors)}
            for item in results
        ]
    }


if __name__ == "__main__":
    mcp.run()
