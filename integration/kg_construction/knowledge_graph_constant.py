import gzip
from pathlib import Path
from typing import Any, Dict
from urllib.parse import quote_plus

from rdflib import Namespace, URIRef

NS = Namespace("https://w3id.org/secure-chain/")
SCHEMA = Namespace("http://schema.org/")

SOFTWARE_CONAN_NS_NEW = Namespace("https://conan.io/center/recipes/")
SOFTWARE_DEBIAN_NS_NEW = Namespace("https://sources.debian.org/src/")
SOFTWARE_GITHUB_NS_NEW = Namespace("https://github.com/")
SOFTWARE_RUST_NS_NEW = Namespace("https://crates.io/crates/")

HARDWARE_NS_NEW = Namespace("https://www.google.com/search?q=")
HARDWARE_VERSION_NS_NEW = Namespace("https://www.google.com/search?q=")
VENDOR_NS_NEW = Namespace("https://www.google.com/search?q=")
LICENSE_NS_NEW = Namespace("https://spdx.org/licenses/")
CWE_NS_NEW = Namespace("https://cwe.mitre.org/data/definitions/")
CVE_NS_NEW = Namespace("https://nvd.nist.gov/vuln/detail/")
GOOGLE_SEARCH_NS_NEW = Namespace("https://www.google.com/search?q=")

PROPERTY_CONTRIBUTOR = SCHEMA.contributor
PROPERTY_DEPENDS_ON = NS.dependsOn
PROPERTY_DISCOVER = NS.discover
PROPERTY_HAS_HARDWARE_VERSION = NS.hasHardwareVersion
PROPERTY_HAS_SOFTWARE_VERSION = NS.hasSoftwareVersion
PROPERTY_IDENTIFIER = SCHEMA.identifier
PROPERTY_LICENSE = SCHEMA.license
PROPERTY_MANUFACTURER = SCHEMA.manufacturer
PROPERTY_OPERATES_ON = NS.operatesOn
PROPERTY_NAME = SCHEMA.name
PROPERTY_PRODUCER = SCHEMA.producer
PROPERTY_VULNERABILITY_TYPE = NS.vulnerabilityType
PROPERTY_VULNERABLE_TO = NS.vulnerableTo
PROPERTY_CPE23 = NS.cpe23

PROPERTY_URL = SCHEMA.url
PROPERTY_VERSION_NAME = NS.versionName
PROPERTY_PROGRAMMING_LANGUAGE = SCHEMA.programmingLanguage
PROPERTY_ECOSYSTEM = NS.ecosystem

DEPS_DEV_ECOSYSTEMS: Dict[str, Dict[str, Any]] = {
    "cargo": {  # Rust / crates.io
        "lang": "Rust",
        "eco": "Cargo",
        "pkg_ns": "https://crates.io/crates/",
        "ver_base": "https://crates.io/crates/",
        "upper": str.lower,  # crates.io 包名小写
    },
    "pypi": {  # Python / PyPI
        "lang": "Python",
        "eco": "PyPI",
        "pkg_ns": "https://pypi.org/project/",
        "ver_base": "https://pypi.org/project/",
        "upper": str,  # PyPI 包名区分大小写
    },
    "npm": {  # JavaScript / npm
        "lang": "JavaScript",
        "eco": "npm",
        "pkg_ns": "https://www.npmjs.com/package/",
        "ver_base": "https://www.npmjs.com/package/",
        "upper": str,  # npm 包名区分大小写
    },
    "maven": {  # Java / Maven Central
        "lang": "Java",
        "eco": "Maven",
        "pkg_ns": "https://mvnrepository.com/artifact/",
        "ver_base": "https://mvnrepository.com/artifact/",
        "upper": str,  # Maven 包名区分大小写
    },
    "go": {  # Go / pkg.go.dev
        "lang": "Go",
        "eco": "Go",
        "pkg_ns": "https://pkg.go.dev/",
        "ver_base": "https://pkg.go.dev/",
        "upper": str,  # Go 包名区分大小写
    },
}


def encoded_uri(base: Namespace, frag: str) -> str:
    return f"{str(base)}{quote_plus(frag.strip())}"


def safe_uri(base: Namespace, frag: str) -> URIRef:
    return URIRef(encoded_uri(base, frag))


def vendor_uri(vendor_name: str) -> URIRef:
    return URIRef(f"{VENDOR_NS_NEW}{quote_plus(vendor_name)}")


def hardware_uri(hardware_name: str) -> URIRef:
    return URIRef(f"{HARDWARE_NS_NEW}{quote_plus(hardware_name)}")


def conan_pkg_uri(recipe: str) -> URIRef:
    recipe_enc = quote_plus(recipe.strip(), safe=".-")  # 保留点和连字符
    return URIRef(f"{SOFTWARE_CONAN_NS_NEW}{recipe_enc}")


def conan_version_uri(recipe: str, version: str) -> URIRef:
    recipe_enc = quote_plus(recipe.strip(), safe=".-")  # 保留点和连字符
    version_enc = quote_plus(version.strip(), safe=".-")
    return URIRef(f"{SOFTWARE_CONAN_NS_NEW}{recipe_enc}?version={version_enc}")


def debian_pkg_uri(pkg_name: str) -> URIRef:
    return URIRef(f"{SOFTWARE_DEBIAN_NS_NEW}{quote_plus(pkg_name, safe='.-+~')}/")


def debian_version_uri(pkg: str, ver: str) -> URIRef:
    pkg_enc = quote_plus(pkg, safe=".-+~")
    ver_enc = quote_plus(ver, safe=".-+~")
    return URIRef(f"{SOFTWARE_DEBIAN_NS_NEW}{pkg_enc}/{ver_enc}/")


def github_repo_uri(repo_url: str) -> URIRef:
    return URIRef(repo_url.rstrip("/"))


def github_version_uri(repo_url: str, tag: str) -> URIRef:
    return URIRef(
        f"{repo_url.rstrip('/')}/releases/tag/{quote_plus(tag.strip(), safe='.-_')}"
    )


def deps_dev_pkg_uri(ec: str, name: str) -> URIRef:
    cfg = DEPS_DEV_ECOSYSTEMS[ec]
    n = cfg["upper"](name)
    return URIRef(f"{cfg['pkg_ns']}{quote_plus(n, safe='.-+~*')}/")


def deps_dev_ver_uri(ec: str, name: str, ver: str) -> URIRef:
    cfg = DEPS_DEV_ECOSYSTEMS[ec]
    n = cfg["upper"](name)
    return URIRef(
        f"{cfg['ver_base']}"
        f"{quote_plus(n, safe='.-+~*')}/"
        f"{quote_plus(ver, safe='.-+~*')}/"
    )


def license_uri(lic_id: str) -> URIRef:
    return URIRef(f"{LICENSE_NS_NEW}{quote_plus(lic_id, safe='.-+~*')}.html")


def google_search_uri(*parts: str) -> URIRef:
    query = "+".join(quote_plus(p.strip(), safe=".-+~*") for p in parts if p.strip())
    return URIRef(f"{GOOGLE_SEARCH_NS_NEW}{query}")


def cve_uri(cve_id: str) -> URIRef:
    return URIRef(f"{CVE_NS_NEW}{quote_plus(cve_id, safe='.-+~*')}")


def cwe_uri(cwe_id: str) -> URIRef:
    return URIRef(f"{CWE_NS_NEW}{quote_plus(cwe_id, safe='.-+~*')}.html")


def _open_text_maybe_gz(fp: Path):
    if fp.suffix == ".gz" or fp.name.endswith(".jsonl.gz"):
        return gzip.open(fp, mode="rt", encoding="utf-8")
    return open(fp, mode="r", encoding="utf-8")


def _worker_id():
    import multiprocessing as mp

    ident = mp.current_process()._identity
    return (ident[0] - 1) if ident else 0
