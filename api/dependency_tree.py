import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from utils import (
    CycleStrategy,
    DedupStrategy,
    _bindings,
    _val,
    run_sparql,
    sparql_escape_literal,
)


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
