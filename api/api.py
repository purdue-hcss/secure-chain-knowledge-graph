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

Run:
  pip install fastapi uvicorn httpx
  uvicorn api:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Literal, Set
import asyncio

import httpx
from fastapi import FastAPI, Query, HTTPException

app = FastAPI(title="SecureChain Dependency API", version="2.0.0")

# Update to your real SPARQL endpoint
SPARQL_ENDPOINT = "https://frink.apps.renci.org/securechainkg/sparql"


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


# ----------------------------
# Flat endpoint: /dependencies
# ----------------------------


def build_flat_query(
    library_name: str,
    library_version: str,
    ecosystem: Optional[str],
    transitive: bool,
) -> str:
    lib = sparql_escape_literal(library_name)
    ver = sparql_escape_literal(library_version)

    # direct vs indirect-only
    if transitive:
        depends_clause = "?libVersion sc:dependsOn/sc:dependsOn+ ?dependencyVersion ."
    else:
        depends_clause = "?libVersion sc:dependsOn ?dependencyVersion ."

    if ecosystem is not None and ecosystem.strip() != "":
        eco = sparql_escape_literal(ecosystem.strip())
        return f"""
PREFIX sc: <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?ecosystem ?dependencyName ?dependencyVersionName ?dependencyEcosystem
WHERE {{
  VALUES (?libName ?libVerName ?ecoIn) {{ ("{lib}" "{ver}" "{eco}") }}

  ?lib schema:name ?libName ;
       sc:hasSoftwareVersion ?libVersion ;
       sc:ecosystem ?ecosystem .
  FILTER(?ecosystem = ?ecoIn)

  ?libVersion sc:versionName ?libVerName .
  {depends_clause}

  ?dependencyVersion sc:versionName ?dependencyVersionName .
  ?dependencyLib sc:hasSoftwareVersion ?dependencyVersion ;
                 schema:name ?dependencyName .
  OPTIONAL {{ ?dependencyLib sc:ecosystem ?dependencyEcosystem . }}
}}
""".strip()

    return f"""
PREFIX sc: <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?ecosystem ?dependencyName ?dependencyVersionName ?dependencyEcosystem
WHERE {{
  VALUES (?libName ?libVerName) {{ ("{lib}" "{ver}") }}

  ?lib schema:name ?libName ;
       sc:hasSoftwareVersion ?libVersion .
  OPTIONAL {{ ?lib sc:ecosystem ?ecosystem . }}

  ?libVersion sc:versionName ?libVerName .
  {depends_clause}

  ?dependencyVersion sc:versionName ?dependencyVersionName .
  ?dependencyLib sc:hasSoftwareVersion ?dependencyVersion ;
                 schema:name ?dependencyName .
  OPTIONAL {{ ?dependencyLib sc:ecosystem ?dependencyEcosystem . }}
}}
""".strip()


def parse_flat_result(result_json: Dict[str, Any]) -> Dict[str, Any]:
    deps: List[Dict[str, str]] = []
    eco_vals: List[str] = []

    for b in _bindings(result_json):
        eco = _val(b, "ecosystem")
        if eco:
            eco_vals.append(eco)

        dep_name = _val(b, "dependencyName")
        dep_ver = _val(b, "dependencyVersionName")
        dep_eco = _val(b, "dependencyEcosystem")

        if dep_name is not None and dep_ver is not None:
            item = {"dependencyName": dep_name, "dependencyVersionName": dep_ver}
            if dep_eco is not None:
                item["dependencyEcosystem"] = dep_eco
            deps.append(item)

    deps.sort(key=lambda x: (x["dependencyName"], x["dependencyVersionName"]))

    eco_unique = sorted(set(eco_vals))
    ecosystem_out: Any
    if len(eco_unique) == 0:
        ecosystem_out = None
    elif len(eco_unique) == 1:
        ecosystem_out = eco_unique[0]
    else:
        ecosystem_out = eco_unique

    return {"ecosystem": ecosystem_out, "dependencies": deps}


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


@dataclass(frozen=True)
class NodeKey:
    name: str
    version: str
    ecosystem: Optional[str] = (
        None  # used only if you want eco-sensitive dedup; default dedup ignores it
    )


def make_dedup_key(
    name: str, version: str, ecosystem: Optional[str], strategy: DedupStrategy
) -> str:
    if strategy == "by_name":
        return name
    # by_version:
    return f"{name}@{version}"


def build_root_info_query(
    library_name: str, library_version: str, ecosystem: Optional[str]
) -> str:
    """
    Fetch root existence + optional root ecosystem, with optional ecosystem constraint.
    """
    lib = sparql_escape_literal(library_name)
    ver = sparql_escape_literal(library_version)

    if ecosystem is not None and ecosystem.strip() != "":
        eco = sparql_escape_literal(ecosystem.strip())
        return f"""
PREFIX sc: <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?ecosystem
WHERE {{
  VALUES (?libName ?libVerName ?ecoIn) {{ ("{lib}" "{ver}" "{eco}") }}

  ?lib schema:name ?libName ;
       sc:hasSoftwareVersion ?libVersion ;
       sc:ecosystem ?ecosystem .
  FILTER(?ecosystem = ?ecoIn)

  ?libVersion sc:versionName ?libVerName .
}}
""".strip()

    return f"""
PREFIX sc: <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?ecosystem
WHERE {{
  VALUES (?libName ?libVerName) {{ ("{lib}" "{ver}") }}

  ?lib schema:name ?libName ;
       sc:hasSoftwareVersion ?libVersion .
  OPTIONAL {{ ?lib sc:ecosystem ?ecosystem . }}

  ?libVersion sc:versionName ?libVerName .
}}
""".strip()


def build_direct_deps_query(
    library_name: str, library_version: str, ecosystem: Optional[str] = None
) -> str:
    """
    Fetch direct dependencies for a node.
    (No ecosystem constraint here; this endpoint returns all deps for all nodes.)
    """
    lib = sparql_escape_literal(library_name)
    ver = sparql_escape_literal(library_version)

    if ecosystem is not None and ecosystem.strip() != "":
        eco = sparql_escape_literal(ecosystem.strip())
        return f"""
PREFIX sc: <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?depName ?depVer ?depEco
WHERE {{
  VALUES (?libName ?libVerName ?ecoIn) {{ ("{lib}" "{ver}" "{eco}") }}

  ?lib schema:name ?libName ;
       sc:hasSoftwareVersion ?libVersion ;
       sc:ecosystem ?ecoIn .


  ?libVersion sc:versionName ?libVerName ;
              sc:dependsOn ?depVersion .

  ?depVersion sc:versionName ?depVer .

  ?depLib sc:hasSoftwareVersion ?depVersion ;
          schema:name ?depName .

  OPTIONAL {{ ?depLib sc:ecosystem ?depEco . }}
}}
""".strip()

    return f"""
PREFIX sc: <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?depName ?depVer ?depEco
WHERE {{
  VALUES (?libName ?libVerName) {{ ("{lib}" "{ver}") }}

    ?lib schema:name ?libName ;
            sc:hasSoftwareVersion ?libVersion .
    ?libVersion sc:versionName ?libVerName ;
                sc:dependsOn ?depVersion .
    ?depVersion sc:versionName ?depVer .
    ?depLib sc:hasSoftwareVersion ?depVersion ;
            schema:name ?depName .
    OPTIONAL {{ ?depLib sc:ecosystem ?depEco . }}
}}
""".strip()


async def fetch_root_ecosystem(
    library_name: str,
    library_version: str,
    ecosystem_filter: Optional[str],
) -> Optional[str]:
    q = build_root_info_query(library_name, library_version, ecosystem_filter)
    result_json = await run_sparql(q)
    ecos: Set[str] = set()
    for b in _bindings(result_json):
        e = _val(b, "ecosystem")
        if e:
            ecos.add(e)

    # If ecosystem_filter is provided, and root doesn't match, bindings might be empty.
    if len(_bindings(result_json)) == 0:
        # No match / not found
        return None

    if len(ecos) == 0:
        return None
    if len(ecos) == 1:
        return next(iter(ecos))
    # Rare: multiple ecosystem values; pick stable smallest
    return sorted(ecos)[0]


async def fetch_direct_deps(
    library_name: str,
    library_version: str,
    ecosystem: Optional[str] = None,
) -> List[Tuple[str, str, Optional[str]]]:
    q = build_direct_deps_query(library_name, library_version, ecosystem)
    result_json = await run_sparql(q)

    out: List[Tuple[str, str, Optional[str]]] = []
    for b in _bindings(result_json):
        dn = _val(b, "depName")
        dv = _val(b, "depVer")
        de = _val(b, "depEco")
        if dn is not None and dv is not None:
            out.append((dn, dv, de))
    out.sort(key=lambda x: (x[0], x[1], x[2] or ""))
    return out


async def build_dependency_tree(
    root_name: str,
    root_version: str,
    root_ecosystem: Optional[str],
    max_depth: int,
    deduped: bool,
    dedup_strategy: DedupStrategy,
    cycle_strategy: CycleStrategy,
    concurrency: int = 10,
) -> Tuple[Dict[str, Any], int]:
    """
    Build a nested dependency tree using DFS with:
    - per-node direct dependency SPARQL queries
    - caching of direct deps by (name,version)
    - cycle detection on current path
    - dedup strategy to avoid repeated expansions across the whole traversal
    """
    # Cache direct deps: (name, version) -> list[(depName, depVer, depEco)]
    dep_cache: Dict[Tuple[str, str], List[Tuple[str, str, Optional[str]]]] = {}

    # Global "expanded" set to prevent expanding same node repeatedly (dedup across entire tree)
    expanded: Set[str] = set()

    # For performance: semaphore to limit concurrent SPARQL calls
    sem = asyncio.Semaphore(concurrency)

    async def get_deps_cached(
        name: str, version: str, ecosystem: Optional[str] = None
    ) -> List[Tuple[str, str, Optional[str]]]:
        key = (name, version)
        if key in dep_cache:
            return dep_cache[key]
        async with sem:
            deps = await fetch_direct_deps(name, version, ecosystem)
        dep_cache[key] = deps
        return deps

    async def dfs(
        name: str,
        version: str,
        ecosystem: Optional[str],
        depth: int,
        path: Set[str],
    ) -> Dict[str, Any]:
        node: Dict[str, Any] = {
            "name": name,
            "version": version,
            "ecosystem": ecosystem,
            "depth": depth,
            "children": [],
        }

        if depth >= max_depth:
            return node

        # Cycle detection on the current path (path is based on dedup key)
        node_id = make_dedup_key(name, version, ecosystem, dedup_strategy)
        if node_id in path:
            if cycle_strategy == "mark":
                node["cycleDetected"] = True
            # cut expansion
            return node

        # Global expansion dedup:
        # If we've already expanded this node elsewhere, we still keep the node,
        # but do not expand its children again (prevents blow-up).
        if deduped and node_id in expanded:
            node["deduped"] = True
            return node

        if deduped:
            expanded.add(node_id)

        # Expand
        next_path = set(path)
        next_path.add(node_id)

        deps = await get_deps_cached(name, version, ecosystem)

        # Build children concurrently (bounded)
        tasks = []
        for dn, dv, de in deps:
            tasks.append(dfs(dn, dv, de, depth + 1, next_path))

        if tasks:
            node["children"] = await asyncio.gather(*tasks)

        return node

    tree = await dfs(root_name, root_version, root_ecosystem, depth=0, path=set())

    # Count nodes in produced tree (including deduped/cycle nodes)
    def count_nodes(n: Dict[str, Any]) -> int:
        c = 1
        for ch in n.get("children", []):
            c += count_nodes(ch)
        return c

    return tree, count_nodes(tree)


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
