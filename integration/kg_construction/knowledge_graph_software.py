from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import os
from pathlib import Path
import re
import tempfile
from threading import RLock
from typing import Optional
from urllib.parse import quote_plus

from knowledge_graph_constant import (
    DEPS_DEV_ECOSYSTEMS,
    NS,
    PROPERTY_CONTRIBUTOR,
    PROPERTY_ECOSYSTEM,
    PROPERTY_HAS_SOFTWARE_VERSION,
    PROPERTY_IDENTIFIER,
    PROPERTY_LICENSE,
    PROPERTY_NAME,
    PROPERTY_PROGRAMMING_LANGUAGE,
    PROPERTY_URL,
    PROPERTY_VERSION_NAME,
    SCHEMA,
    _open_text_maybe_gz,
    _worker_id,
    conan_pkg_uri,
    conan_version_uri,
    debian_pkg_uri,
    debian_version_uri,
    deps_dev_pkg_uri,
    deps_dev_ver_uri,
    github_repo_uri,
    github_version_uri,
    license_uri,
)
from rdflib import RDF, Graph, Literal, URIRef
from tqdm import tqdm


def add_conan_software_version_relations(
    graph: Graph, conan_software_version_file: str
):
    seen_sw = set()
    seen_ver = set()

    with open(conan_software_version_file, "r", encoding="utf-8") as f:
        refs = json.load(f)["conancenter"].keys()

    for ref in tqdm(refs, desc="Adding Conan packages"):
        try:
            recipe, version = ref.split("/", 1)
        except ValueError:
            print(f"[warn] skip malformed ref: {ref}")
            continue

        software_ref = conan_pkg_uri(recipe)
        if software_ref not in seen_sw:
            graph.add((software_ref, RDF.type, NS.Software))
            graph.add((software_ref, PROPERTY_NAME, Literal(recipe)))
            graph.add((software_ref, PROPERTY_PROGRAMMING_LANGUAGE, Literal("C/C++")))
            graph.add((software_ref, PROPERTY_ECOSYSTEM, Literal("Conan")))
            seen_sw.add(software_ref)

        version_ref = conan_version_uri(recipe, version)
        if version_ref not in seen_ver:
            graph.add((version_ref, RDF.type, NS.SoftwareVersion))
            graph.add((version_ref, PROPERTY_VERSION_NAME, Literal(version)))
            seen_ver.add(version_ref)

        graph.add((software_ref, PROPERTY_HAS_SOFTWARE_VERSION, version_ref))


def add_debian_software_version_relations(graph: Graph, debian_pkg_versions_file: str):
    seen_pkg = set()
    seen_ver = set()

    with open(debian_pkg_versions_file, encoding="utf-8") as f:
        pkg_map: dict[str, list[str]] = json.load(f)

    for pkg, version_list in tqdm(pkg_map.items(), desc="Adding Debian packages"):
        pkg_ref = debian_pkg_uri(pkg)

        if pkg_ref not in seen_pkg:
            graph.add((pkg_ref, RDF.type, NS.Software))
            graph.add((pkg_ref, PROPERTY_NAME, Literal(pkg)))
            graph.add((pkg_ref, PROPERTY_PROGRAMMING_LANGUAGE, Literal("C/C++")))
            graph.add((pkg_ref, PROPERTY_ECOSYSTEM, Literal("Debian")))
            seen_pkg.add(pkg_ref)

        for ver in set(version_list):  # 去重
            ver_ref = debian_version_uri(pkg, ver)
            if ver_ref not in seen_ver:
                graph.add((ver_ref, RDF.type, NS.SoftwareVersion))
                graph.add((ver_ref, PROPERTY_VERSION_NAME, Literal(ver)))
                seen_ver.add(ver_ref)

            graph.add((pkg_ref, PROPERTY_HAS_SOFTWARE_VERSION, ver_ref))


def add_github_software_version_relations(
    graph: Graph, github_software_version_file: str, github_repo_meta_file: str
) -> None:
    versions_map = json.load(open(github_software_version_file, encoding="utf-8"))
    meta_map = json.load(open(github_repo_meta_file, encoding="utf-8"))

    seen_repo = set()
    seen_ver = set()
    seen_user = set()
    seen_lic = set()

    for repo_key, version_list in tqdm(
        versions_map.items(), desc="Adding GitHub packages"
    ):
        if repo_key not in meta_map:
            print("meta missing for repo_key, skip", repo_key)
            continue

        meta = meta_map[repo_key]
        repo_url = meta.get(
            "repository_url", f"https://github.com/{quote_plus(repo_key, safe='.-_')}"
        )
        repo_ref = github_repo_uri(repo_url)

        if repo_ref not in seen_repo:
            graph.add((repo_ref, RDF.type, NS.Software))
            graph.add((repo_ref, PROPERTY_NAME, Literal(repo_key)))
            graph.add((repo_ref, PROPERTY_PROGRAMMING_LANGUAGE, Literal("C/C++")))
            graph.add((repo_ref, PROPERTY_ECOSYSTEM, Literal("GitHub")))
            seen_repo.add(repo_ref)

        add_github_repo_contributors(graph, meta, repo_ref, seen_user)

        license_ref = add_github_repo_licenses(graph, meta, repo_ref, seen_lic)

        for tag in set(version_list):
            ver_ref = github_version_uri(repo_url, tag)
            if ver_ref not in seen_ver:
                graph.add((ver_ref, RDF.type, NS.SoftwareVersion))
                graph.add((ver_ref, PROPERTY_VERSION_NAME, Literal(tag)))
                seen_ver.add(ver_ref)
            graph.add((repo_ref, PROPERTY_HAS_SOFTWARE_VERSION, ver_ref))
            if license_ref:
                graph.add((ver_ref, PROPERTY_LICENSE, license_ref))


def add_github_repo_contributors(
    graph: Graph, meta: dict, repo_ref: URIRef, seen_user: set
) -> None:
    for user in meta.get("contributors", []):
        user_ref = URIRef(f"https://github.com/{quote_plus(user, safe='.-_')}")
        if user_ref not in seen_user:
            add_person(graph, user_ref, user)
            seen_user.add(user_ref)
        graph.add((repo_ref, PROPERTY_CONTRIBUTOR, user_ref))


def add_person(graph: Graph, ref: URIRef, name: str) -> None:
    graph.add((ref, RDF.type, SCHEMA.Person))
    graph.add((ref, PROPERTY_NAME, Literal(name)))


def add_github_repo_licenses(
    graph: Graph, meta: dict, repo_ref: URIRef, seen_lic: set
) -> Optional[URIRef]:
    if isinstance(meta.get("licence"), dict):
        lic_id = meta["licence"].get("id")
        lic_name = meta["licence"].get("name", lic_id.upper())
        if lic_id:
            lic_ref = add_license(graph, seen_lic, lic_id, lic_name)
            return lic_ref
    return None


def add_license(
    graph: Graph, seen_lic: set, lic_id: str, lic_name: Optional[str] = None
) -> Optional[URIRef]:
    if lic_id in ["License ID not found", "non-standard", "Unlicense"]:
        return None
    lic_ref = license_uri(lic_id)
    if lic_ref not in seen_lic:
        graph.add((lic_ref, RDF.type, NS.License))
        graph.add((lic_ref, PROPERTY_IDENTIFIER, Literal(lic_id)))
        if lic_name:
            graph.add((lic_ref, PROPERTY_NAME, Literal(lic_name)))
        seen_lic.add(lic_ref)
    return lic_ref


def _process_one_file_to_nt(fp_str: str, ecosystem: str, cfg: dict) -> tuple[str, str, int]:
    """
    worker：处理单个文件，构建局部 Graph，输出到临时 .nt 文件
    返回 (原文件名, nt_file_path)
    """
    fp = Path(fp_str)

    # 给每个 worker 一个自己的进度条位置（主进度条用 position=0）
    wid = _worker_id()
    pos = wid + 1

    pbar = tqdm(
        desc=f"{fp.name}",
        unit="rec",
        position=pos,
        leave=False,   # worker 结束就消失，屏幕更干净
        dynamic_ncols=True,
    )

    g_local = Graph()
    seen_soft, seen_ver, seen_lic = set(), set(), set()
    rec_count = 0

    with _open_text_maybe_gz(fp) as f:
        for line in f:
            if not line.strip():
                continue
            rec_count += 1
            pbar.update(1)

            item = json.loads(line)

            if item.get("System") and item["System"] != ecosystem.upper():
                continue

            name = (item.get("Name") or "").strip()
            version = (item.get("Version") or "").strip()
            if not name or not version:
                continue

            licenses = item.get("Licenses", []) or []
            urls = [
                lnk["URL"]
                for lnk in (item.get("Links") or [])
                if isinstance(lnk, dict) and "URL" in lnk
            ]

            soft_uri = deps_dev_pkg_uri(ecosystem, name)
            if soft_uri not in seen_soft:
                g_local.add((soft_uri, RDF.type, NS.Software))
                g_local.add((soft_uri, PROPERTY_NAME, Literal(name)))
                g_local.add(
                    (soft_uri, PROPERTY_PROGRAMMING_LANGUAGE, Literal(cfg["lang"]))
                )
                g_local.add((soft_uri, PROPERTY_ECOSYSTEM, Literal(cfg["eco"])))
                seen_soft.add(soft_uri)

            ver_uri_ = deps_dev_ver_uri(ecosystem, name, version)
            if ver_uri_ not in seen_ver:
                g_local.add((ver_uri_, RDF.type, NS.SoftwareVersion))
                g_local.add((ver_uri_, PROPERTY_VERSION_NAME, Literal(version)))
                g_local.add((soft_uri, PROPERTY_HAS_SOFTWARE_VERSION, ver_uri_))

                for u in urls:
                    if u:
                        g_local.add((ver_uri_, PROPERTY_URL, Literal(u)))

                for lic_expr in licenses:
                    if not lic_expr:
                        continue
                    for tok in re.split(r"\s+(?:OR|AND|\||\&)\s*", str(lic_expr)):
                        tok = tok.strip()
                        if not tok:
                            continue
                        lic_uri = add_license(g_local, seen_lic, tok)
                        if lic_uri:
                            g_local.add((ver_uri_, PROPERTY_LICENSE, lic_uri))

                seen_ver.add(ver_uri_)

    pbar.close()

    # 写临时 nt 文件（N-Triples 合并最简单）
    fd, nt_path = tempfile.mkstemp(suffix=".nt", prefix=f"depsdev_{fp.stem}_")
    os.close(fd)
    g_local.serialize(destination=nt_path, format="nt", encoding="utf-8")
    return fp.name, nt_path, rec_count


def add_deps_dev_software_version_from_dir(
    versions_dir_path: str, ecosystem: str, max_workers: Optional[int] = 4
) -> list[str]:
    print(f"Adding deps.dev {ecosystem} packages from {versions_dir_path} ...")

    cfg = DEPS_DEV_ECOSYSTEMS[ecosystem]
    files = sorted(Path(versions_dir_path).glob("*.jsonl*"))
    if not files:
        return []

    max_workers = max_workers or (os.cpu_count() or 4)

    tqdm.set_lock(RLock())

    tmp_nt_files = []
    total_pbar = tqdm(desc=f"Streaming {ecosystem} packages", unit="rec", position=0, dynamic_ncols=True)

    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_process_one_file_to_nt, str(fp), ecosystem, cfg) for fp in files]
        for fut in as_completed(futs):
            fname, nt_path, rec_count = fut.result()
            tmp_nt_files.append(nt_path)
            total_pbar.update(rec_count)
            total_pbar.set_postfix(file=fname)

    total_pbar.close()

    return tmp_nt_files  # 返回生成的 nt 文件列表，后续由调用者合并并清理

    # for nt_path in tqdm(tmp_nt_files, desc="Merging graphs", unit="file", position=0, dynamic_ncols=True):
    #     g.parse(nt_path, format="nt")
    #     os.remove(nt_path)
