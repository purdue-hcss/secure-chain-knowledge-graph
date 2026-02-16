import json
import os
import re
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional
from urllib.parse import quote_plus

import pandas as pd
from debian.debian_support import Version
from knowledge_graph_constant import (
    DEPS_DEV_ECOSYSTEMS,
    NS,
    PROPERTY_DEPENDS_ON,
    PROPERTY_ECOSYSTEM,
    PROPERTY_HAS_SOFTWARE_VERSION,
    PROPERTY_NAME,
    PROPERTY_PROGRAMMING_LANGUAGE,
    PROPERTY_VERSION_NAME,
    _open_text_maybe_gz,
    _worker_id,
    conan_version_uri,
    debian_version_uri,
    deps_dev_pkg_uri,
    deps_dev_ver_uri,
    github_version_uri,
    google_search_uri,
)
from rdflib import RDF, Graph, Literal, URIRef
from tqdm import tqdm

_cmp_re: re.Pattern[str] = re.compile(r"^\s*(>=|<=|>>|<<|>|<|=)?\s*([^,&\s]+)\s*$")


def add_conan_depends_on_relations(graph: Graph, depends_csv_file: str) -> None:
    df = pd.read_csv(depends_csv_file)
    added_edges = set()

    for row in tqdm(
        df.itertuples(index=False), total=len(df), desc="Adding dependsOn edges"
    ):
        try:
            src_pkg, src_ver = str(row.Version).split("#", 1)
            tgt_pkg, tgt_ver = str(row.DependsOn).split("#", 1)
        except ValueError:
            print(f"[WARN] malformed line skipped: {row}")
            continue

        src_ref = conan_version_uri(src_pkg, src_ver)
        tgt_ref = conan_version_uri(tgt_pkg, tgt_ver)

        edge = (src_ref, PROPERTY_DEPENDS_ON, tgt_ref)
        if edge not in added_edges:
            graph.add(edge)
            added_edges.add(edge)


def add_debian_depends_on_relations(
    graph: Graph, depends_csv_file: str, debian_pkg_versions_file: str
) -> None:
    with open(debian_pkg_versions_file, encoding="utf-8") as f:
        version_map: Dict[str, List[str]] = json.load(f)

    df = pd.read_csv(depends_csv_file)

    edge_seen: set[tuple] = set()
    tgt_node_seen: set[URIRef] = set()

    for row in tqdm(
        df.itertuples(index=False), total=len(df), desc="Adding Debian dependsOn edges"
    ):
        try:
            src_pkg, src_ver = str(row.Version).split("#", 1)
            tgt_pkg, tgt_expr = str(row.DependsOn).split("#", 1)
        except ValueError:
            print(f"[WARN] malformed line skipped: {row}")
            continue

        src_uri = debian_version_uri(src_pkg, src_ver)

        try:
            constraints = parse_constraints(tgt_expr)
        except ValueError as e:
            print("[WARN]", e)
            continue

        all_tgt_versions = version_map.get(tgt_pkg, [])
        matches = [v for v in all_tgt_versions if satisfies(v, constraints)]

        if not matches:
            continue

        for v in matches:
            tgt_uri = debian_version_uri(tgt_pkg, v)

            # 必要时为目标版本补 type、versionName（可选）
            if tgt_uri not in tgt_node_seen:
                # print(f"[INFO] add {tgt_uri} to graph")
                graph.add((tgt_uri, RDF.type, NS.SoftwareVersion))
                graph.add((tgt_uri, PROPERTY_VERSION_NAME, Literal(v)))
                tgt_node_seen.add(tgt_uri)

            triple = (src_uri, PROPERTY_DEPENDS_ON, tgt_uri)
            if triple not in edge_seen:
                graph.add(triple)
                edge_seen.add(triple)


def add_github_depends_on_relations(
    graph: Graph, depends_csv_file: str, github_repo_meta_file: str
) -> None:
    with open(github_repo_meta_file, encoding="utf-8") as f:
        meta_map = json.load(f)

    def repo_url_of(key: str) -> str:
        return meta_map.get(key, {}).get(
            "repository_url", f"https://github.com/{quote_plus(key, safe='.-_')}"
        )

    df = pd.read_csv(depends_csv_file)  # Version,DependsOn

    seen_soft, seen_ver, seen_edge = set(), set(), set()

    for row in tqdm(
        df.itertuples(index=False), total=len(df), desc="Adding GitHub dependsOn edges"
    ):
        try:
            src_pkg, src_tag = str(row.Version).split("#", 1)
            tgt_pkg, tgt_tag = str(row.DependsOn).split("#", 1)
        except ValueError:
            continue  # 格式不符

        # ---------- 源版本 URI（已在图中） -------------------------
        src_uri = github_version_uri(repo_url_of(src_pkg), src_tag)

        # ---------- 目标 Software 节点 ----------------------------
        tgt_soft_uri = google_search_uri(tgt_pkg)
        if tgt_soft_uri not in seen_soft:
            graph.add((tgt_soft_uri, RDF.type, NS.Software))
            graph.add((tgt_soft_uri, PROPERTY_NAME, Literal(tgt_pkg)))
            graph.add((tgt_soft_uri, PROPERTY_PROGRAMMING_LANGUAGE, Literal("C/C++")))
            graph.add((tgt_soft_uri, PROPERTY_ECOSYSTEM, Literal("Unknown")))
            seen_soft.add(tgt_soft_uri)

        # -- 目标 SoftwareVersion --
        tgt_ver_uri = google_search_uri(tgt_pkg, tgt_tag)
        if tgt_ver_uri not in seen_ver:
            graph.add((tgt_ver_uri, RDF.type, NS.SoftwareVersion))
            graph.add((tgt_ver_uri, PROPERTY_VERSION_NAME, Literal(tgt_tag)))
            graph.add((tgt_soft_uri, PROPERTY_HAS_SOFTWARE_VERSION, tgt_ver_uri))
            seen_ver.add(tgt_ver_uri)

        # -- dependsOn 边 --
        edge = (src_uri, PROPERTY_DEPENDS_ON, tgt_ver_uri)
        if edge not in seen_edge:
            graph.add(edge)
            seen_edge.add(edge)


def parse_constraints(expr: str):
    """
    把 '>=1.2&<2.0' or '1.4.2' or '*' 拆成 [(op, ver), ...].
    '*' → [('*', None)]
    无符号 → '='
    支持 & 或 , 作为 AND 连接
    """
    expr = expr.strip()
    if expr == "*" or expr == "":
        return [("*", None)]

    clauses = re.split(r"[&,]", expr)
    out = []
    for cl in clauses:
        m = _cmp_re.match(cl)
        if not m:
            raise ValueError(f"cannot parse constraint: {cl}")
        op = m.group(1) or "="
        ver = m.group(2)
        out.append((op, ver))
    return out


def satisfies(ver: str, constraints) -> bool:
    """ver: candidate version str; constraints: [(op, ver2), ...]"""
    v = Version(ver)
    for op, rhs in constraints:
        if op == "*" or (op in ("=", "==") and rhs == "*"):
            return True
        cmp = cmp_version_obj(v, Version(rhs))
        if (
            (op in ("=", "==") and cmp != 0)
            or (op in (">", ">>") and cmp <= 0)  # ← 新增  >>
            or (op in ("<", "<<") and cmp >= 0)  # ← 新增  <<
            or (op == ">=" and cmp < 0)
            or (op == "<=" and cmp > 0)
        ):
            return False
    # print(f"version {ver} satisfies constraints {constraints}")
    return True


def cmp_version_obj(va: Version, vb: Version) -> int:
    if va < vb:
        return -1
    if va > vb:
        return 1
    return 0


def _process_one_deps_file_to_nt(
    fp_str: str, ecosystem: str, cfg: dict
) -> tuple[str, str, int]:
    """
    worker：处理单个 dependsOn 文件，构建局部图，写出 nt。
    返回 (原文件名, nt_path, record_count)
    """
    fp = Path(fp_str)

    # 主进度条 position=0；worker 从 1 开始
    wid = _worker_id()
    pos = wid + 1

    # worker 内进度条（实时更新）
    wbar = tqdm(
        desc=f"{fp.name}",
        unit="rec",
        position=pos,
        leave=False,
        dynamic_ncols=True,
    )

    g_local = Graph()
    seen_soft, seen_ver, seen_edge = set(), set(), set()
    rec_count = 0

    with _open_text_maybe_gz(fp) as f:
        for line in f:
            if not line.strip():
                continue
            rec_count += 1
            wbar.update(1)

            rec = json.loads(line)
            frm, to = rec.get("From", {}), rec.get("To", {})

            if (
                frm.get("System") != ecosystem.upper()
                or to.get("System") != ecosystem.upper()
            ):
                continue

            fname_f, fver = (
                (frm.get("Name", "") or "").strip(),
                (frm.get("Version", "") or "").strip(),
            )
            tname, tver = (
                (to.get("Name", "") or "").strip(),
                (to.get("Version", "") or "").strip(),
            )
            if not (fname_f and fver and tname and tver):
                continue

            frm_uri = deps_dev_ver_uri(ecosystem, fname_f, fver)

            # To side software + version
            tsoft_uri = deps_dev_pkg_uri(ecosystem, tname)
            if tsoft_uri not in seen_soft:
                g_local.add((tsoft_uri, RDF.type, NS.Software))
                g_local.add((tsoft_uri, PROPERTY_NAME, Literal(tname)))
                g_local.add(
                    (tsoft_uri, PROPERTY_PROGRAMMING_LANGUAGE, Literal(cfg["lang"]))
                )
                g_local.add((tsoft_uri, PROPERTY_ECOSYSTEM, Literal(cfg["eco"])))
                seen_soft.add(tsoft_uri)

            tver_uri = deps_dev_ver_uri(ecosystem, tname, tver)
            if tver_uri not in seen_ver:
                g_local.add((tver_uri, RDF.type, NS.SoftwareVersion))
                g_local.add((tver_uri, PROPERTY_VERSION_NAME, Literal(tver)))
                g_local.add((tsoft_uri, PROPERTY_HAS_SOFTWARE_VERSION, tver_uri))
                seen_ver.add(tver_uri)

            edge = (frm_uri, PROPERTY_DEPENDS_ON, tver_uri)
            if edge not in seen_edge:
                g_local.add(edge)
                seen_edge.add(edge)

    wbar.close()

    fd, nt_path = tempfile.mkstemp(suffix=".nt", prefix=f"depsdev_dep_{fp.stem}_")
    os.close(fd)
    g_local.serialize(destination=nt_path, format="nt", encoding="utf-8")
    return fp.name, nt_path, rec_count


def add_deps_dev_depends_on_from_dir(
    deps_dir_path: str, ecosystem: str, max_workers: Optional[int] = 4
) -> list[str]:
    """
    从目录读取多个 deps.dev 导出的 *.jsonl.gz / *.jsonl 文件，
    为同一 ecosystem 批量添加 dependsOn 关系与相关实体。
    """
    print(f"Adding deps.dev {ecosystem} dependsOn edges from {deps_dir_path} ...")
    cfg = DEPS_DEV_ECOSYSTEMS[ecosystem]

    files = sorted(Path(deps_dir_path).glob("*.jsonl*"))
    if not files:
        return []

    max_workers = max_workers or (os.cpu_count() or 4)

    tqdm.set_lock(RLock())

    tmp_nt_files: list[str] = []

    total = tqdm(
        desc=f"Streaming {ecosystem} dependsOn edges",
        unit="record",
        position=0,
        dynamic_ncols=True,
    )

    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        futs = [
            ex.submit(_process_one_deps_file_to_nt, str(fp), ecosystem, cfg)
            for fp in files
        ]

        for fut in as_completed(futs):
            fname, nt_path, rec_count = fut.result()
            tmp_nt_files.append(nt_path)

            # 总进度条更新 + 显示当前完成的文件
            total.update(rec_count)
            total.set_postfix(file=fname)

    total.close()

    return tmp_nt_files  # 返回生成的 nt 文件列表，后续由调用者合并并清理

    # # 合并阶段（顺序）
    # for nt_path in tqdm(
    #     tmp_nt_files, desc="Merging graphs", unit="file", position=0, dynamic_ncols=True
    # ):
    #     g.parse(nt_path, format="nt")
    #     try:
    #         os.remove(nt_path)
    #     except OSError:
    #         pass
