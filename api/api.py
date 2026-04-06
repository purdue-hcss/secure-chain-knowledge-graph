"""
api.py

FastAPI service for querying dependencies from a SPARQL endpoint.

Endpoints:
1) GET /dependencies
   - Flat list of dependencies
   - transitive=false (default): direct only
   - transitive=true: indirect only (>=2 hops)
   - optional ecosystem filter on the ROOT library

2) GET /dependency-tree
   - NO transitive parameter
   - Returns ALL direct + indirect dependencies as a nested tree
   - Includes depth for each node (root depth=0)
   - optional ecosystem filter on the ROOT library
   - max_depth controls expansion depth
   - cycle handling + dedup strategies

3) GET /dependents
   - Flat list of dependents (reverse of dependencies)
   - transitive=false (default): direct dependents only
   - transitive=true: indirect dependents only (>=2 hops)
   - optional ecosystem filter on the TARGET library

Run:
  pip install fastapi uvicorn httpx
  uvicorn api:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from utils import CycleStrategy, DedupStrategy, run_sparql
from fastapi import FastAPI, HTTPException, Query

from dependencies import build_flat_query, parse_flat_result
from dependency_tree import build_dependency_tree, fetch_root_ecosystem
from dependents import build_dependents_query, parse_dependents_result

app = FastAPI(title="SecureChain Dependency API", version="2.0.0")


# ----------------------------
# Flat endpoint: /dependencies
# ----------------------------


@app.get("/dependencies")
async def get_dependencies(
    library_name: str = Query(..., min_length=1),
    library_version: str = Query(..., min_length=1),
    ecosystem: Optional[str] = Query(
        None, description="Optional ecosystem filter for the ROOT library"
    ),
    transitive: bool = Query(
        False,
        description="false=direct only (default); true=indirect only (>=2 hops)",
    ),
):
    q = build_flat_query(library_name, library_version, ecosystem, transitive)
    result_json = await run_sparql(q)
    parsed = parse_flat_result(result_json)

    return {
        "libraryName": library_name,
        "libraryVersionName": library_version,
        "ecosystemFilter": ecosystem,
        "transitive": transitive,
        "ecosystem": parsed["ecosystem"],
        "count": len(parsed["dependencies"]),
        "dependencies": parsed["dependencies"],
    }


# ---------------------------------------
# Tree endpoint: /dependency-tree (ALL deps)
# ---------------------------------------


@app.get("/dependency-tree")
async def get_dependency_tree(
    library_name: str = Query(..., min_length=1),
    library_version: str = Query(..., min_length=1),
    ecosystem: Optional[str] = Query(
        None, description="Optional ecosystem filter for the ROOT library"
    ),
    max_depth: int = Query(
        10, ge=0, le=50, description="Max depth to expand (root depth=0)"
    ),
    include_root: bool = Query(True, description="If false, return only root children"),
    deduped: bool = Query(
        True,
        description="If true, globally deduplicate nodes; if false, expand fully per path",
    ),
    dedup_strategy: DedupStrategy = Query(
        "by_version", description="Dedup strategy: by_version or by_name"
    ),
    cycle_strategy: CycleStrategy = Query(
        "cut", description="Cycle strategy: cut or mark"
    ),
    concurrency: int = Query(
        10, ge=1, le=50, description="Max concurrent SPARQL calls while expanding tree"
    ),
):
    # Validate / locate root (and apply optional ecosystem constraint)
    root_eco = await fetch_root_ecosystem(library_name, library_version, ecosystem)

    # If user supplied ecosystem and it doesn't match (or root not found), we treat as not found
    if ecosystem is not None and ecosystem.strip() != "" and root_eco is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Root library/version not found or ecosystem mismatch",
                "libraryName": library_name,
                "libraryVersionName": library_version,
                "ecosystemFilter": ecosystem,
            },
        )

    # Build tree (all direct+indirect)
    tree, node_count = await build_dependency_tree(
        root_name=library_name,
        root_version=library_version,
        root_ecosystem=root_eco,
        max_depth=max_depth,
        deduped=deduped,
        dedup_strategy=dedup_strategy,
        cycle_strategy=cycle_strategy,
        concurrency=concurrency,
    )

    payload: Dict[str, Any] = {
        "libraryName": library_name,
        "libraryVersionName": library_version,
        "ecosystemFilter": ecosystem,
        "maxDepth": max_depth,
        "includeRoot": include_root,
        "deduped": deduped,
        "dedupStrategy": dedup_strategy,
        "cycleStrategy": cycle_strategy,
        "nodeCount": node_count,
    }

    if include_root:
        payload["tree"] = tree
    else:
        payload["tree"] = tree.get("children", [])

    return payload


# ---------------------------------------
# Dependents endpoint: /dependents
# ---------------------------------------


@app.get("/dependents")
async def get_dependents(
    library_name: str = Query(..., min_length=1),
    library_version: Optional[str] = Query(
        None,
        description="Optional target library version; if omitted, return dependents of all versions of the library",
    ),
    ecosystem: Optional[str] = Query(
        None,
        description="Optional ecosystem filter for the TARGET library",
    ),
    transitive: bool = Query(
        False,
        description="false=direct dependents only (default); true=indirect dependents only (>=2 hops)",
    ),
):
    q = build_dependents_query(library_name, library_version, ecosystem, transitive)
    result_json = await run_sparql(q)
    parsed = parse_dependents_result(result_json)

    return {
        "libraryName": library_name,
        "libraryVersionName": library_version,
        "ecosystemFilter": ecosystem,
        "transitive": transitive,
        "count": len(parsed["dependents"]),
        "dependents": parsed["dependents"],
    }
