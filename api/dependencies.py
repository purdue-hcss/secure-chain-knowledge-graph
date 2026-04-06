from typing import Any, Dict, List, Optional

from utils import _bindings, _val, sparql_escape_literal


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
