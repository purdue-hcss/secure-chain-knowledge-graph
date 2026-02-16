from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF
from pathlib import Path
import json
from typing import Optional, Tuple
from tqdm import tqdm

from knowledge_graph_constant import (
    NS,
    PROPERTY_DEPENDS_ON,
    PROPERTY_ECOSYSTEM,
    PROPERTY_HAS_SOFTWARE_VERSION,
    PROPERTY_NAME,
    PROPERTY_PROGRAMMING_LANGUAGE,
    PROPERTY_VERSION_NAME,
    PROPERTY_VULNERABLE_TO,
    conan_pkg_uri,
    conan_version_uri,
    cve_uri,
)


def _strip_revision(s: str) -> str:
    # "name/ver#rrev" -> "name/ver"；"name/ver@u/c#rrev" -> "name/ver@u/c"
    return s.split("#", 1)[0] if s else s


def _core_label(s: str) -> str:
    return _strip_revision((s or "").strip())


def _parse_name_version(ref_or_label: str) -> Tuple[Optional[str], Optional[str]]:
    """
    尝试从 Conan 的 label/ref 中解析 name 与 version：
    - 形如 "openssl/1.1.1w" 或 "openssl/1.1.1w@user/channel"
    """
    core = _core_label(ref_or_label)
    # 去掉 @user/channel
    core = core.split("@", 1)[0]
    if "/" in core:
        name, ver = core.split("/", 1)
        name, ver = name.strip(), ver.strip()
        if name and ver:
            return name, ver
    return None, None


def ensure_software(graph: Graph, name: str) -> URIRef:
    sref = conan_pkg_uri(name)
    # 幂等：添加相同三元组不会重复
    graph.add((sref, RDF.type, NS.Software))
    graph.add((sref, PROPERTY_NAME, Literal(name)))
    graph.add((sref, PROPERTY_PROGRAMMING_LANGUAGE, Literal("C/C++")))
    graph.add((sref, PROPERTY_ECOSYSTEM, Literal("Conan")))
    return sref


def ensure_software_version(graph: Graph, name: str, version: str) -> URIRef:
    sref = ensure_software(graph, name)
    vref = conan_version_uri(name, version)
    graph.add((vref, RDF.type, NS.SoftwareVersion))
    graph.add((vref, PROPERTY_VERSION_NAME, Literal(version)))
    graph.add((sref, PROPERTY_HAS_SOFTWARE_VERSION, vref))
    return vref


def add_vulnerabilities_for_version(graph: Graph, version_ref: URIRef, vuln_list):
    """
    vuln_list 来自 OSS Index component report 的 "vulnerabilities" 数组。
    常见字段：id, title, description, cvssScore, cwe, reference, externalReferences...
    """
    if not isinstance(vuln_list, list):
        return
    for v in vuln_list:
        vid = v.get("id") or v.get("cve") or v.get("displayName")
        if not vid:
            continue
        vref = cve_uri(vid)
        graph.add((version_ref, PROPERTY_VULNERABLE_TO, vref))


def add_all_from_conan(graph: Graph, json_path: str):
    """
    读取 conan_index.json：
    - 创建 Software 与 SoftwareVersion；
    - 挂接 dependsOn（只建“直接依赖”）；
    - 挂接 hasVulnerability（基于 OSS Index 结果）。
    """
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    pkgs = data.get("packages", [])
    if not isinstance(pkgs, list):
        raise ValueError("Invalid JSON: 'packages' 应为数组")

    for pkg_entry in tqdm(pkgs, desc="Software & Versions & Links"):
        pkg_name = pkg_entry.get("name")
        if not pkg_name:
            continue

        # 先确保 Software 节点存在
        _ = ensure_software(graph, pkg_name)

        versions = pkg_entry.get("versions", []) or []
        for ver_obj in versions:
            version = ver_obj.get("version")
            if not version:
                continue

            # 版本节点
            vref = ensure_software_version(graph, pkg_name, version)
            # 依赖（direct == True）
            deps = ver_obj.get("dependencies") or []
            for dep in deps:
                # 优先从 dep["ref"] / dep["label"] 抓 name & version
                cand = dep.get("ref") or dep.get("label")
                dname, dver = _parse_name_version(cand or "")
                if not dname or not dver:
                    # 兜底：有些节点字段（极少）
                    dname = dep.get("name")
                    dver = dep.get("version")
                if not dname or not dver:
                    continue  # 无法解析则跳过

                # 依赖版本也要保证存在（并连回其 Software）
                # 这里没有 purl（可从 dep 中其它字段补）；先用 None
                dvref = ensure_software_version(graph, dname, dver)

                # 建立版本级依赖边：version -> dependsOn -> dep_version
                graph.add((vref, PROPERTY_DEPENDS_ON, dvref))

            # 漏洞（来自合并后的版本字段）
            vulns = ver_obj.get("vulnerabilities")
            add_vulnerabilities_for_version(graph, vref, vulns)
