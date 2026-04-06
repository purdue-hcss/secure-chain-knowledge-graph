from typing import Any, Dict, List, Optional

from utils import _bindings, _val, sparql_escape_literal


def build_dependents_query(
    library_name: str,
    library_version: Optional[str],
    ecosystem: Optional[str],
    transitive: bool,
) -> str:
    lib = sparql_escape_literal(library_name)

    if transitive:
        depends_clause = "?dependentVersion sc:dependsOn/sc:dependsOn+ ?targetVersion ."
    else:
        depends_clause = "?dependentVersion sc:dependsOn ?targetVersion ."

    version_filter = ""
    values_clause = f'VALUES (?targetName) {{ ("{lib}") }}'

    if library_version is not None and library_version.strip() != "":
        ver = sparql_escape_literal(library_version.strip())
        values_clause = f'VALUES (?targetName ?targetVerName) {{ ("{lib}" "{ver}") }}'
        version_filter = "?targetVersion sc:versionName ?targetVerName ."

    if ecosystem is not None and ecosystem.strip() != "":
        eco = sparql_escape_literal(ecosystem.strip())

        if library_version is not None and library_version.strip() != "":
            values_clause = f'VALUES (?targetName ?targetVerName ?ecoIn) {{ ("{lib}" "{ver}" "{eco}") }}'
        else:
            values_clause = f'VALUES (?targetName ?ecoIn) {{ ("{lib}" "{eco}") }}'

        return f"""
PREFIX sc: <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT
  ?targetVersionName
  ?dependentName
  ?dependentVersionName
  ?dependentEcosystem
WHERE {{
  {values_clause}

  ?targetLib schema:name ?targetName ;
             sc:hasSoftwareVersion ?targetVersion ;
             sc:ecosystem ?targetEcosystem .

  FILTER(?targetEcosystem = ?ecoIn)

  {version_filter}

  OPTIONAL {{ ?targetVersion sc:versionName ?targetVersionName . }}

  {depends_clause}

  ?dependentVersion sc:versionName ?dependentVersionName .

  ?dependentLib sc:hasSoftwareVersion ?dependentVersion ;
                schema:name ?dependentName .

  OPTIONAL {{ ?dependentLib sc:ecosystem ?dependentEcosystem . }}
}}
""".strip()

    return f"""
PREFIX sc: <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT
  ?targetVersionName
  ?dependentName
  ?dependentVersionName
  ?dependentEcosystem
WHERE {{
  {values_clause}

  ?targetLib schema:name ?targetName ;
             sc:hasSoftwareVersion ?targetVersion .

  {version_filter}

  OPTIONAL {{ ?targetVersion sc:versionName ?targetVersionName . }}

  {depends_clause}

  ?dependentVersion sc:versionName ?dependentVersionName .

  ?dependentLib sc:hasSoftwareVersion ?dependentVersion ;
                schema:name ?dependentName .

  OPTIONAL {{ ?dependentLib sc:ecosystem ?dependentEcosystem . }}
}}
""".strip()


def parse_dependents_result(result_json: Dict[str, Any]) -> Dict[str, Any]:
    dependents: List[Dict[str, str]] = []

    for b in _bindings(result_json):
        dep_name = _val(b, "dependentName")
        dep_ver = _val(b, "dependentVersionName")
        dep_eco = _val(b, "dependentEcosystem")
        target_ver = _val(b, "targetVersionName")

        if dep_name is not None and dep_ver is not None:
            item = {
                "dependentName": dep_name,
                "dependentVersionName": dep_ver,
            }
            if dep_eco is not None:
                item["dependentEcosystem"] = dep_eco
            if target_ver is not None:
                item["targetLibraryVersionName"] = target_ver

            dependents.append(item)

    dependents.sort(
        key=lambda x: (
            x["dependentName"],
            x["dependentVersionName"],
            x.get("targetLibraryVersionName", ""),
        )
    )

    return {
        "dependents": dependents,
    }
