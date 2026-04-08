# Update to your real SPARQL endpoint
from typing import Any, Dict, List, Literal, Optional

import httpx
from fastapi import HTTPException

SPARQL_ENDPOINT = "https://hcss.cs.purdue.edu/securechain_graphdb/repositories/securechain"


DedupStrategy = Literal["by_version", "by_name"]
CycleStrategy = Literal["cut", "mark"]


def sparql_escape_literal(s: str) -> str:
    """Escape user-provided strings to be safely embedded as SPARQL string literals (without outer quotes)."""
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


async def run_sparql(query: str) -> Dict[str, Any]:
    """
    SPARQL Protocol: POST query as application/sparql-query, expect JSON results.
    Adjust if your endpoint requires form-encoded data.
    """
    headers = {
        "Accept": "application/sparql-results+json",
        "Content-Type": "application/sparql-query; charset=utf-8",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            SPARQL_ENDPOINT, content=query.encode("utf-8"), headers=headers
        )

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "SPARQL endpoint error",
                "status_code": resp.status_code,
                "body": resp.text[:2000],
            },
        )

    try:
        return resp.json()
    except Exception:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Invalid JSON from SPARQL endpoint",
                "body": resp.text[:2000],
            },
        )


def _bindings(result_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    return result_json.get("results", {}).get("bindings", [])


def _val(binding: Dict[str, Any], var: str) -> Optional[str]:
    x = binding.get(var)
    if not x:
        return None
    return x.get("value")
