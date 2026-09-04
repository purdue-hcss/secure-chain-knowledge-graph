---
name: secure-chain-knowledge-graph
description: Use for software supply-chain questions about software/hardware versions, dependencies, CVEs, CWEs, licenses, people, and organizations.
metadata:
  iri: "https://w3id.org/secure-chain"
---

# Secure Chain Knowledge Graph

## 1. What this graph represents

The Secure Chain Knowledge Graph models software, software versions, hardware, hardware versions, dependencies, vulnerabilities, vulnerability types, licenses, people, and organizations in software supply chains. Its ontology extends Schema.org and is documented as Secure Chain Ontology release 1.0.0 (2024-10-20); the public KG integrates cross-ecosystem records such as software packages, CVEs, and CWEs. The documented vocabulary supports dependency tracing, vulnerability impact analysis, hardware compatibility, license inspection, and vulnerability-discovery attribution.

This skill covers only the classes and predicates documented at <https://purdue-hcss.github.io/secure-chain-ontology/>. The documentation does not publish entity counts, a refresh cadence, canonical instance-IRI patterns, or a distinct named-graph IRI. It also does not define CVSS scores, exploit status, patch dates, advisory timelines, or license-compatibility rules.

## 2. Answerable question archetypes

- Given a software name and version label, return matching vulnerabilities (for example, CVE identifiers) and vulnerability types (for example, CWE identifiers).
- Given a software version, return the software versions it directly depends on.
- Given a vulnerable dependency version or CVE, return software versions that directly depend on the affected version.
- Given a software or hardware product, return its known versions and descriptive metadata.
- Return software versions that operate on a named hardware version.
- Given a vulnerability, return its type and the people or organizations that discovered it.
- Return documented licenses, code repositories, programming languages, contributors, producers, or manufacturers for matching resources.
- Aggregate distinct vulnerabilities by vulnerability type for a software product.
- Join an asset inventory or SBOM graph to SecureChain only when both graphs expose the same exact resource IRI or a normalized shared identifier and version label.

Explicitly NOT answerable here: CVSS severity, exploit availability, remediation or patch status, advisory publication chronology, runtime deployment state, source-code-level vulnerability analysis, or legal license compatibility unless another graph supplies those facts. AI/ML behavioral threats such as prompt injection and model poisoning belong to the separate AISecureChain graph. No general cross-graph identity mapping is documented.

## 3. Namespaces

```sparql
PREFIX sc:     <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
```

The slash in the `sc:` namespace and the `http` scheme in the `schema:` namespace are significant.

## 4. Core classes (entity types)

| Class IRI (`rdf:type`) | Meaning | Approx. count | Primary key / IRI pattern |
|---|---|---:|---|
| `sc:Software` | A software application in a secure supply chain; subclass of `schema:SoftwareApplication` | Not published | Source-derived IRI; find via `schema:name` and, when present, `schema:identifier` |
| `sc:SoftwareVersion` | A specific software version; subclass of `sc:Software` | Not published | Source-derived IRI; resolve from a parent software node through `sc:hasSoftwareVersion` and `sc:versionName` |
| `sc:Hardware` | A hardware product in a secure supply chain; subclass of `schema:Product` | Not published | Source-derived IRI; find via `schema:name` and, when present, `schema:identifier` |
| `sc:HardwareVersion` | A specific hardware version; subclass of `sc:Hardware` | Not published | Source-derived IRI; resolve from a parent hardware node through `sc:hasHardwareVersion` and `sc:versionName` |
| `sc:Vulnerability` | A vulnerability affecting supply-chain components; subclass of `schema:Intangible` | Not published | Source-derived IRI; normally retrieve the CVE-like key with `schema:identifier` |
| `sc:VulnerabilityType` | A vulnerability classification; subclass of `schema:Intangible` | Not published | Source-derived IRI; normally retrieve the CWE-like key with `schema:identifier` |
| `sc:License` | A software or hardware license; subclass of `schema:CreativeWork` | Not published | Source-derived IRI; inspect `schema:name` or `schema:identifier` when present |
| `schema:Person` | A person, including a possible vulnerability discoverer or contributor | Not published | Source-derived IRI; inspect `schema:givenName`, `schema:familyName`, `schema:name`, or `schema:email` |
| `schema:Organization` | An organization, including a possible discoverer, affiliation, producer, or manufacturer | Not published | Source-derived IRI; inspect `schema:name` or `schema:identifier` when present |
| `schema:Product` | Reused Schema.org superclass for products | Not published | No SecureChain-specific pattern documented |
| `schema:SoftwareApplication` | Reused Schema.org superclass for software applications | Not published | No SecureChain-specific pattern documented |

`sc:SoftwareVersion` and `sc:HardwareVersion` are modeled as subclasses of their corresponding product classes, not as disjoint version-only types.

## 5. Key predicates

The ontology declares no minimum, maximum, or functional cardinality axioms. `0..*` therefore means “not constrained by the ontology,” not that every resource is expected to have many values. For reused Schema.org predicates, the arrows below describe their intended query role; SecureChain does not add local OWL domain/range constraints to them.

| Predicate | Domain → Range | Cardinality | Object value space / examples |
|---|---|---:|---|
| `sc:hasSoftwareVersion` | `sc:Software` → `sc:SoftwareVersion` | 0..* | Version resource IRIs |
| `sc:hasHardwareVersion` | `sc:Hardware` → `sc:HardwareVersion` | 0..* | Hardware-version resource IRIs |
| `sc:dependsOn` | `sc:SoftwareVersion` → `sc:SoftwareVersion` | 0..* | Directed edge from the dependent version to the dependency version |
| `sc:operatesOn` | `sc:SoftwareVersion` → `sc:HardwareVersion` | 0..* | Hardware-version resource IRIs |
| `sc:vulnerableTo` | `sc:SoftwareVersion` → `sc:Vulnerability` | 0..* | Vulnerability resource IRIs, commonly described by CVE identifiers |
| `sc:vulnerabilityType` | `sc:Vulnerability` → `sc:VulnerabilityType` | 0..* | Type resource IRIs, commonly described by CWE identifiers |
| `sc:discover` | `schema:Person` or `schema:Organization` → `sc:Vulnerability` | 0..* | Vulnerability resource IRIs; note the discoverer is the subject |
| `schema:license` | Resource → `sc:License` or another license resource | 0..* | License resource IRIs; local domain/range is not constrained |
| `schema:contributor` | Resource → `schema:Person` or `schema:Organization` | 0..* | Contributor resource IRIs; local domain/range is not constrained |
| `schema:affiliation` | `schema:Person` → `schema:Organization` | 0..* | Organization resource IRIs; local domain/range is not constrained |
| `schema:manufacturer` | Product/resource → `schema:Organization` | 0..* | Manufacturer resource IRIs; local domain/range is not constrained |
| `schema:producer` | Product/resource → `schema:Person` or `schema:Organization` | 0..* | Producer resource IRIs; local domain/range is not constrained |
| `sc:versionName` | `sc:SoftwareVersion` or `sc:HardwareVersion` → `xsd:string` | 0..* | Literal version label, e.g. `"5.6.0"`; no SemVer normalization is declared |
| `schema:name` | Resource → literal | 0..* | Human-readable name such as `"openssl"` or `"xz-utils"` |
| `schema:identifier` | Resource → literal | 0..* | Source identifier such as a CVE, CWE, package, or organization identifier |
| `schema:description` | Resource → literal | 0..* | Free-text description |
| `schema:codeRepository` | Resource → literal | 0..* | Repository URL/string; datatype is not constrained locally |
| `schema:programmingLanguage` | Resource → literal | 0..* | Language name or code; no controlled vocabulary is declared |
| `schema:url` | Resource → literal | 0..* | URL lexical value; datatype is not constrained locally |
| `schema:email` | Resource → literal | 0..* | Email lexical value; datatype is not constrained locally |
| `schema:givenName` | `schema:Person` → literal | 0..* | Given-name text; local domain/range is not constrained |
| `schema:familyName` | `schema:Person` → literal | 0..* | Family-name text; local domain/range is not constrained |

## 6. Literal & value conventions

- Version labels: `sc:versionName` has range `xsd:string`. Match the stored lexical form exactly unless the user explicitly asks for looser matching; do not compare versions numerically or assume SemVer ordering.
- Names and identifiers: use `schema:name` and `schema:identifier`. Data comes from heterogeneous ecosystems, so discover a resource by name/identifier before traversing version edges; do not construct instance IRIs from guessed patterns.
- CVE/CWE values: CVEs are `sc:Vulnerability` instances and CWEs are `sc:VulnerabilityType` instances, normally exposed through `schema:identifier`. No controlled instance-IRI stem is documented.
- Language tags and datatypes: except for `sc:versionName`, the ontology does not constrain literal datatypes or language tags. Use `STR(?value)` before case conversion or equality when heterogeneous literal forms are possible.
- Text search: no full-text extension is documented. Use standard SPARQL such as `FILTER(LCASE(STR(?name)) = "openssl")` for exact case-insensitive matching or `FILTER(CONTAINS(LCASE(STR(?name)), "iphone"))` for substring matching.
- Dates: the ontology release metadata uses `xsd:date`, but the documented domain vocabulary has no date predicate for vulnerabilities, software releases, patches, or advisories.
- Graph targeting: the documented public endpoint is `https://frink.apps.renci.org/securechainkg/sparql` and its official examples query the default dataset. No public named-graph IRI is documented. Queries below use `SERVICE` so they remain targetable from a federating MCP query layer.

## 7. Example queries (NL → SPARQL)

**Q: “Find the versions recorded for OpenSSL.”**

```sparql
PREFIX sc:     <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?software ?softwareName ?version ?versionName
WHERE {
  SERVICE <https://frink.apps.renci.org/securechainkg/sparql> {
    ?software a sc:Software ;
              schema:name ?softwareName ;
              sc:hasSoftwareVersion ?version .
    ?version sc:versionName ?versionName .
    FILTER(LCASE(STR(?softwareName)) = "openssl")
  }
}
ORDER BY STR(?versionName)
```

**Q: “Which CVEs affect xz-utils version 5.6.0?”**

```sparql
PREFIX sc:     <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?softwareName ?versionName ?cve ?cveId
WHERE {
  SERVICE <https://frink.apps.renci.org/securechainkg/sparql> {
    ?software a sc:Software ;
              schema:name ?softwareName ;
              sc:hasSoftwareVersion ?version .
    ?version sc:versionName ?versionName ;
             sc:vulnerableTo ?cve .
    ?cve a sc:Vulnerability ;
         schema:identifier ?cveId .
    FILTER(LCASE(STR(?softwareName)) = "xz-utils")
    FILTER(STR(?versionName) = "5.6.0")
  }
}
ORDER BY STR(?cveId)
```

**Q: “What does OpenSSL version 3.0.0 directly depend on?”**

```sparql
PREFIX sc:     <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?dependencySoftware ?dependencyName ?dependencyVersion ?dependencyVersionName
WHERE {
  SERVICE <https://frink.apps.renci.org/securechainkg/sparql> {
    ?software a sc:Software ;
              schema:name ?softwareName ;
              sc:hasSoftwareVersion ?sourceVersion .
    ?sourceVersion sc:versionName ?sourceVersionName ;
                   sc:dependsOn ?dependencyVersion .
    ?dependencySoftware a sc:Software ;
                        schema:name ?dependencyName ;
                        sc:hasSoftwareVersion ?dependencyVersion .
    ?dependencyVersion sc:versionName ?dependencyVersionName .
    FILTER(LCASE(STR(?softwareName)) = "openssl")
    FILTER(STR(?sourceVersionName) = "3.0.0")
  }
}
ORDER BY LCASE(STR(?dependencyName)) STR(?dependencyVersionName)
```

**Q: “Which software versions directly depend on a version affected by CVE-2024-3094?”**

```sparql
PREFIX sc:     <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT
  ?dependentSoftwareName ?dependentVersionName
  ?vulnerableDependencyName ?vulnerableDependencyVersionName
WHERE {
  SERVICE <https://frink.apps.renci.org/securechainkg/sparql> {
    ?cve a sc:Vulnerability ;
         schema:identifier ?cveId .
    FILTER(UCASE(STR(?cveId)) = "CVE-2024-3094")

    ?vulnerableDependencyVersion sc:vulnerableTo ?cve ;
                                   sc:versionName ?vulnerableDependencyVersionName .
    ?vulnerableDependency a sc:Software ;
                          schema:name ?vulnerableDependencyName ;
                          sc:hasSoftwareVersion ?vulnerableDependencyVersion .

    ?dependentVersion sc:dependsOn ?vulnerableDependencyVersion ;
                      sc:versionName ?dependentVersionName .
    ?dependentSoftware a sc:Software ;
                       schema:name ?dependentSoftwareName ;
                       sc:hasSoftwareVersion ?dependentVersion .
  }
}
ORDER BY LCASE(STR(?dependentSoftwareName)) STR(?dependentVersionName)
```

**Q: “For xz-utils, how many distinct CVEs fall under each CWE?”**

```sparql
PREFIX sc:     <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT ?cweId (COUNT(DISTINCT ?cve) AS ?cveCount)
WHERE {
  SERVICE <https://frink.apps.renci.org/securechainkg/sparql> {
    ?software a sc:Software ;
              schema:name ?softwareName ;
              sc:hasSoftwareVersion ?version .
    FILTER(LCASE(STR(?softwareName)) = "xz-utils")

    ?version sc:vulnerableTo ?cve .
    ?cve sc:vulnerabilityType ?cwe .
    ?cwe schema:identifier ?cweId .
  }
}
GROUP BY ?cweId
ORDER BY DESC(?cveCount) STR(?cweId)
```

**Q: “Which software versions operate on an iPhone hardware version?”**

```sparql
PREFIX sc:     <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?softwareName ?softwareVersionName ?hardwareName ?hardwareVersionName
WHERE {
  SERVICE <https://frink.apps.renci.org/securechainkg/sparql> {
    ?hardware a sc:Hardware ;
              schema:name ?hardwareName ;
              sc:hasHardwareVersion ?hardwareVersion .
    FILTER(CONTAINS(LCASE(STR(?hardwareName)), "iphone"))
    ?hardwareVersion sc:versionName ?hardwareVersionName .

    ?softwareVersion a sc:SoftwareVersion ;
                     sc:operatesOn ?hardwareVersion ;
                     sc:versionName ?softwareVersionName .
    ?software a sc:Software ;
              schema:name ?softwareName ;
              sc:hasSoftwareVersion ?softwareVersion .
  }
}
ORDER BY LCASE(STR(?hardwareName)) STR(?hardwareVersionName) LCASE(STR(?softwareName))
```

**Q: “What licenses are attached to OpenSSL or its versions?”**

```sparql
PREFIX sc:     <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?softwareName ?versionName ?licenseScope ?license ?licenseName ?licenseId
WHERE {
  SERVICE <https://frink.apps.renci.org/securechainkg/sparql> {
    ?software a sc:Software ;
              schema:name ?softwareName .
    FILTER(LCASE(STR(?softwareName)) = "openssl")

    {
      ?software schema:license ?license .
      BIND("product" AS ?licenseScope)
    }
    UNION
    {
      ?software sc:hasSoftwareVersion ?version .
      ?version sc:versionName ?versionName ;
               schema:license ?license .
      BIND("version" AS ?licenseScope)
    }

    OPTIONAL { ?license schema:name ?licenseName }
    OPTIONAL { ?license schema:identifier ?licenseId }
  }
}
ORDER BY STR(?versionName) LCASE(STR(?licenseName))
```

**Q: “Which entries in another software-inventory graph match SecureChain versions with known vulnerabilities?” (cross-graph template)**

```sparql
PREFIX sc:     <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?asset ?softwareName ?secureChainVersion ?cveId
WHERE {
  # Replace this placeholder with the actual inventory graph IRI.
  GRAPH <urn:replace-with:software-inventory-graph> {
    ?asset a schema:SoftwareApplication ;
           schema:identifier ?sharedSoftwareId ;
           schema:softwareVersion ?inventoryVersion .
  }

  SERVICE <https://frink.apps.renci.org/securechainkg/sparql> {
    ?software a sc:Software ;
              schema:identifier ?sharedSoftwareId ;
              schema:name ?softwareName ;
              sc:hasSoftwareVersion ?version .
    ?version sc:versionName ?secureChainVersion ;
             sc:vulnerableTo ?cve .
    ?cve schema:identifier ?cveId .
    FILTER(STR(?secureChainVersion) = STR(?inventoryVersion))
  }
}
ORDER BY STR(?asset) STR(?cveId)
```

The cross-graph template is valid only when the inventory graph and SecureChain use the same normalized `schema:identifier` and compatible version strings. Prefer an exact shared resource IRI when one exists.

## 8. Gotchas & performance

- `metadata.iri` uses the canonical ontology identifier because no separate data-graph IRI is documented. Do not assume the public endpoint contains a named graph called `<https://w3id.org/secure-chain>`; its official examples query the default dataset.
- When sending a query directly to `https://frink.apps.renci.org/securechainkg/sparql`, remove the outer `SERVICE` block and run its contents as the main graph pattern. Retain `SERVICE` when a federating MCP query layer must target this endpoint alongside other graphs.
- Use `sc:` as `<https://w3id.org/secure-chain/>`. The ontology IRI itself is `<https://w3id.org/secure-chain>` without the trailing slash, but class and property IRIs use the slash namespace.
- Use `schema:` as `<http://schema.org/>`, not the HTTPS form, so predicates match stored data.
- `sc:dependsOn` points from a dependent software version to the dependency version. Reverse-impact queries must traverse this predicate backward by placing the potentially affected version in object position.
- Avoid unbounded transitive paths such as `sc:dependsOn+` on the full graph. Query one hop first; for bounded depth, use a small explicit `UNION` of fixed-length paths and apply software/version filters as early as possible.
- Version strings are lexical labels. Sorting them with `ORDER BY` is lexical, not semantic-version ordering; pre-releases and mixed ecosystem formats make numeric casting unsafe.
- Names originate in heterogeneous ecosystems and may collide or vary in punctuation. Use `schema:identifier` and version labels to disambiguate whenever available, and do not merge resources solely because their lowercase names match.
- Most predicates are optional and multi-valued. Use `OPTIONAL` for nonessential metadata and `DISTINCT` when joining versions, vulnerabilities, types, contributors, or licenses.
- `sc:SoftwareVersion` is a subclass of `sc:Software`, and `sc:HardwareVersion` is a subclass of `sc:Hardware`. Do not rely on subclass inference unless the target triplestore advertises RDFS/OWL reasoning; query the explicit type needed by the pattern.
- The ontology declares reused Schema.org properties without SecureChain-specific domain/range restrictions. Do not reject a triple merely because its subject differs from the common role shown in §5.
- Listing a component's licenses is supported, but deciding whether a set of licenses is legally compatible requires a separate policy/rules graph.
