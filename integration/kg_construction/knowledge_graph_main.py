import os
import shutil
from pathlib import Path

from knowledge_graph_base import construct_base_graph
from knowledge_graph_conan import add_all_from_conan
from knowledge_graph_dependency import add_deps_dev_depends_on_from_dir
from knowledge_graph_software import add_deps_dev_software_version_from_dir
from knowledge_graph_vulnerability import (
    add_deps_dev_advisory_vulnerability_from_dir,
    add_vulnerabilities_from_nvdcve,
    add_vulnerability_types_from_cwe,
)
from rdflib import Graph
from tqdm import tqdm

CONAN_INDEX_FILE_PATH = "resources/conan/conan_index.json"

KNOWLEDGE_GRAPH_BASE_SAVING_PATH = "resources/graph/secure-chain-base.nt"
KNOWLEDGE_GRAPH_BASE_TEMP_PATH = "resources/graph/secure-chain-base-temp.nt"
KNOWLEDGE_GRAPH_CONAN_SAVING_PATH = "resources/graph/secure-chain-conan.nt"
KNOWLEDGE_GRAPH_GO_SAVING_PATH = "resources/graph/secure-chain-go.nt"
KNOWLEDGE_GRAPH_JAVA_SAVING_PATH = "resources/graph/secure-chain-java.nt"
KNOWLEDGE_GRAPH_JAVASCRIPT_SAVING_PATH = "resources/graph/secure-chain-javascript.nt"
KNOWLEDGE_GRAPH_PYTHON_SAVING_PATH = "resources/graph/secure-chain-python.nt"
KNOWLEDGE_GRAPH_RUST_SAVING_PATH = "resources/graph/secure-chain-rust.nt"
KNOWLEDGE_GRAPH_VULNERABILITY_SAVING_PATH = (
    "resources/graph/secure-chain-vulnerability.nt"
)


def save_graph(g: Graph, file_path: str, buffer_size=1 << 20):
    print(f"Saving graph to {file_path} ...")
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    # g.serialize(destination=file_path, format="turtle")
    g.serialize(
        destination=file_path,
        format="nt",
        encoding="utf-8",
        buffering=buffer_size,
    )
    print(f"Graph saved to {file_path}.")


def concat_graph(out_path: str, nt_paths: list[str]) -> None:
    print(f"Concatenating {len(nt_paths)} graphs into {out_path} ...")
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as w:
        for p in tqdm(
            nt_paths,
            desc="Concatenating graphs",
            unit="file",
            position=0,
            dynamic_ncols=True,
        ):
            with open(p, "rb") as r:
                shutil.copyfileobj(r, w, length=1024 * 1024 * 16)  # 16MB buffer

    for p in nt_paths:
        try:
            os.remove(p)
        except OSError:
            pass

    print(f"Concatenated graph saved to {out_path}.")


def main():
    graph = construct_base_graph()
    save_graph(graph, KNOWLEDGE_GRAPH_BASE_SAVING_PATH)

    graph = construct_base_graph()
    add_all_from_conan(graph, CONAN_INDEX_FILE_PATH)
    save_graph(graph, KNOWLEDGE_GRAPH_CONAN_SAVING_PATH)

    graph = construct_base_graph()
    save_graph(graph, KNOWLEDGE_GRAPH_BASE_TEMP_PATH)
    version_parts = add_deps_dev_software_version_from_dir(
        "resources/dep-dev-data/go_versions", "go"
    )
    dep_parts = add_deps_dev_depends_on_from_dir("resources/dep-dev-data/go_deps", "go")
    adv_parts = add_deps_dev_advisory_vulnerability_from_dir(
        "resources/dep-dev-data/go_versions",
        "resources/dep-dev-data/advisories_2025-09-29.jsonl",
        "go",
    )
    concat_graph(KNOWLEDGE_GRAPH_GO_SAVING_PATH, version_parts + dep_parts + adv_parts)

    graph = construct_base_graph()
    save_graph(graph, KNOWLEDGE_GRAPH_BASE_TEMP_PATH)
    version_parts = add_deps_dev_software_version_from_dir(
        "resources/dep-dev-data/java_versions", "maven"
    )
    dep_parts = add_deps_dev_depends_on_from_dir(
        "resources/dep-dev-data/java_deps", "maven"
    )
    adv_parts = add_deps_dev_advisory_vulnerability_from_dir(
        "resources/dep-dev-data/java_versions",
        "resources/dep-dev-data/advisories_2025-09-29.jsonl",
        "maven",
    )
    concat_graph(
        KNOWLEDGE_GRAPH_JAVA_SAVING_PATH, version_parts + dep_parts + adv_parts
    )

    graph = construct_base_graph()
    save_graph(graph, KNOWLEDGE_GRAPH_BASE_TEMP_PATH)
    version_parts = add_deps_dev_software_version_from_dir(
        "resources/dep-dev-data/javascript_versions", "npm"
    )
    dep_parts = add_deps_dev_depends_on_from_dir(
        "resources/dep-dev-data/javascript_deps", "npm"
    )
    adv_parts = add_deps_dev_advisory_vulnerability_from_dir(
        "resources/dep-dev-data/javascript_versions",
        "resources/dep-dev-data/advisories_2025-09-29.jsonl",
        "npm",
    )
    concat_graph(
        KNOWLEDGE_GRAPH_JAVASCRIPT_SAVING_PATH, version_parts + dep_parts + adv_parts
    )

    graph = construct_base_graph()
    save_graph(graph, KNOWLEDGE_GRAPH_BASE_TEMP_PATH)
    version_parts = add_deps_dev_software_version_from_dir(
        "resources/dep-dev-data/python_versions", "pypi"
    )
    dep_parts = add_deps_dev_depends_on_from_dir(
        "resources/dep-dev-data/python_deps", "pypi"
    )
    adv_parts = add_deps_dev_advisory_vulnerability_from_dir(
        "resources/dep-dev-data/python_versions",
        "resources/dep-dev-data/advisories_2025-09-29.jsonl",
        "pypi",
    )
    concat_graph(
        KNOWLEDGE_GRAPH_PYTHON_SAVING_PATH, version_parts + dep_parts + adv_parts
    )

    graph = construct_base_graph()
    save_graph(graph, KNOWLEDGE_GRAPH_BASE_TEMP_PATH)
    version_parts = add_deps_dev_software_version_from_dir(
        "resources/dep-dev-data/rust_versions", "cargo"
    )
    dep_parts = add_deps_dev_depends_on_from_dir(
        "resources/dep-dev-data/rust_deps", "cargo"
    )
    adv_parts = add_deps_dev_advisory_vulnerability_from_dir(
        "resources/dep-dev-data/rust_versions",
        "resources/dep-dev-data/advisories_2025-09-29.jsonl",
        "cargo",
    )
    concat_graph(
        KNOWLEDGE_GRAPH_RUST_SAVING_PATH, version_parts + dep_parts + adv_parts
    )

    graph = construct_base_graph()
    add_vulnerabilities_from_nvdcve(graph, nvdcve_dir="resources/cve/nvdcve")
    add_vulnerability_types_from_cwe(graph, cwe_dir="resources/cwe")
    save_graph(graph, KNOWLEDGE_GRAPH_VULNERABILITY_SAVING_PATH)


if __name__ == "__main__":
    main()
