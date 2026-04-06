# Dependency Query API

A RESTful API for querying software dependencies from an RDF knowledge graph using SPARQL.
The API supports:

* Flat dependency queries (direct or indirect)
* Full nested dependency tree queries
* Reverse dependency queries (dependents)
* Optional ecosystem filtering
* Depth-aware dependency traversal

---

## Base URL

```
http://<host>:<port>
```

Example:

```
https://purdue-hcss.github.io/nsf-software-supply-chain_security/api
```

---

# 1️⃣ Flat Dependency API

## Endpoint

### `GET /dependencies`

Retrieve dependencies for a given library and version.

---

## Query Parameters

| Parameter         | Type      | Required | Default | Description                                                                                       |
| ----------------- | --------- | -------- | ------- | ------------------------------------------------------------------------------------------------- |
| `library_name`    | `string`  | Yes      | –       | Name of the target library (e.g., `openssl`)                                                      |
| `library_version` | `string`  | Yes      | –       | Version name of the target library (e.g., `3.0.10`)                                               |
| `ecosystem`       | `string`  | No       | `null`  | Ecosystem filter (e.g., `pypi`, `npm`, `maven`). If omitted, no ecosystem restriction is applied. |
| `transitive`      | `boolean` | No       | `false` | Whether to return indirect dependencies (≥2 hops). `false` returns direct dependencies only.      |

---

### Notes on `transitive`

* `transitive=false` (default): **direct dependencies only**
* `transitive=true`: **indirect dependencies only** (dependencies at distance ≥ 2)
* Direct dependencies are **not included** when `transitive=true`

---

## Request Examples

### Direct dependencies (default)

```
https://purdue-hcss.github.io/nsf-software-supply-chain_security/api/dependencies?library_name=pandas&library_version=2.2.3
```

### Indirect dependencies

```
https://purdue-hcss.github.io/nsf-software-supply-chain_security/api/dependencies?library_name=pandas&library_version=2.2.3&transitive=true
```

---

## Response Format

```json
{
  "libraryName": "pandas",
  "libraryVersionName": "2.2.3",
  "ecosystemFilter": null,
  "transitive": false,
  "ecosystem": "PyPI",
  "count": 3,
  "dependencies": [
    {
      "dependencyName": "numpy",
      "dependencyVersionName": "2.2.5",
      "dependencyEcosystem": "PyPI"
    },
    {
      "dependencyName": "python-dateutil",
      "dependencyVersionName": "2.9.0.post0",
      "dependencyEcosystem": "PyPI"
    },
    {
      "dependencyName": "tzdata",
      "dependencyVersionName": "2025.2.0",
      "dependencyEcosystem": "PyPI"
    }
  ]
}
```

---

# 2️⃣ Dependency Tree API (Full Nested Graph)

## Endpoint

### `GET /dependency-tree`

Return **all direct and indirect dependencies** as a nested tree structure.

Unlike `/dependencies`, this endpoint:

* Does NOT use a `transitive` parameter
* Always returns the full dependency graph
* Includes `depth` for each node
* Returns dependencies as nested children

---

## Query Parameters

| Parameter         | Type      | Required | Default      | Description                                               |
| ----------------- | --------- | -------- | ------------ | --------------------------------------------------------- |
| `library_name`    | `string`  | Yes      | –            | Target library name                                       |
| `library_version` | `string`  | Yes      | –            | Target version                                            |
| `ecosystem`       | `string`  | No       | `null`       | Optional ecosystem constraint applied to the root library |
| `max_depth`       | `integer` | No       | `10`         | Maximum expansion depth (root = depth 0)                  |
| `include_root`    | `boolean` | No       | `true`       | Whether to include the root node in the response          |
| `deduped`         | `boolean` | No       | `false`      | Whether to deduplicate nodes in the tree                  |
| `dedup_strategy`  | `string`  | No       | `by_version` | `by_version` or `by_name`                                 |
| `cycle_strategy`  | `string`  | No       | `cut`        | `cut` (default) or `mark`                                 |
| `concurrency`     | `integer` | No       | `10`         | Max concurrent SPARQL calls for tree expansion            |

---

## Depth Semantics

| Level | Meaning               |
| ----- | --------------------- |
| `0`   | Root package          |
| `1`   | Direct dependencies   |
| `2+`  | Indirect dependencies |

---

## Request Example

```
https://purdue-hcss.github.io/nsf-software-supply-chain_security/api/dependency-tree?library_name=pandas&library_version=2.2.3
```

---

## Response Format

```json
{
  "libraryName": "pandas",
  "libraryVersionName": "2.2.3",
  "ecosystemFilter": null,
  "maxDepth": 10,
  "includeRoot": true,
  "deduped": true,
  "dedupStrategy": "by_version",
  "cycleStrategy": "cut",
  "nodeCount": 5,
  "tree": {
    "name": "pandas",
    "version": "2.2.3",
    "ecosystem": "PyPI",
    "depth": 0,
    "children": [
      {
        "name": "numpy",
        "version": "2.2.5",
        "ecosystem": "PyPI",
        "depth": 1,
        "children": []
      },
      {
        "name": "python-dateutil",
        "version": "2.9.0.post0",
        "ecosystem": "PyPI",
        "depth": 1,
        "children": [
          {
            "name": "six",
            "version": "1.17.0",
            "ecosystem": "PyPI",
            "depth": 2,
            "children": []
          }
        ]
      },
      {
        "name": "tzdata",
        "version": "2025.2.0",
        "ecosystem": "PyPI",
        "depth": 1,
        "children": []
      }
    ]
  }
}
```

---

## Tree Node Schema

Each node contains:

| Field           | Type                 | Description                                            |
| --------------- | -------------------- | ------------------------------------------------------ |
| `name`          | `string`             | Library name                                           |
| `version`       | `string`             | Version                                                |
| `ecosystem`     | `string \| null`     | Ecosystem if available                                 |
| `depth`         | `integer`            | Dependency depth                                       |
| `children`      | `array`              | Nested dependencies                                    |
| `cycleDetected` | `boolean` (optional) | Present only if cycle_strategy=mark                    |
| `deduped`       | `boolean` (optional) | Present if node expansion skipped due to deduplication |

---

## Dedup Strategies

### `by_version` (default)

Deduplicate using `(name, version)`

### `by_name`

Deduplicate using `name` only

---

## Cycle Strategies

### `cut` (default)

Stop expansion when a cycle is detected.

### `mark`

Include the node and mark:

```json
{
  "cycleDetected": true
}
```

---

# 3️⃣ Reverse Dependency API

## Endpoint

### `GET /dependents`

Retrieve all libraries that depend on a given library.

---

## Query Parameters

| Parameter         | Type      | Required | Default | Description                                             |
| ----------------- | --------- | -------- | ------- | ------------------------------------------------------- |
| `library_name`    | `string`  | Yes      | –       | Target library name                                     |
| `library_version` | `string`  | No       | `null`  | Optional version. If omitted, query across all versions |
| `ecosystem`       | `string`  | No       | `null`  | Optional ecosystem filter                               |
| `transitive`      | `boolean` | No       | `false` | Whether to return indirect dependents (≥2 hops)         |

---

## Behavior

* If `library_version` is provided:

  * Return dependents of that specific version

* If `library_version` is omitted:

  * Return dependents of **all versions**
  * Each result may include:

    * `targetLibraryVersionName`

---

## Request Examples

```bash
# Direct dependents
curl "https://purdue-hcss.github.io/nsf-software-supply-chain_security/api/dependents?library_name=zlib"

# Indirect dependents
curl "https://purdue-hcss.github.io/nsf-software-supply-chain_security/api/dependents?library_name=zlib&transitive=true"

# Specific version
curl "https://purdue-hcss.github.io/nsf-software-supply-chain_security/api/dependents?library_name=zlib&library_version=1.2.13"
```

---

## Response Example

```json
{
  "libraryName": "zlib",
  "libraryVersionName": null,
  "ecosystemFilter": null,
  "transitive": false,
  "count": 2,
  "dependents": [
    {
      "dependentName": "ffmpeg",
      "dependentVersionName": "4.2.1",
      "dependentEcosystem": "Conan",
      "targetLibraryVersionName": "1.2.13"
    }
  ]
}
```

---

## Dependent Object

| Field                      | Type   | Description                      |
| -------------------------- | ------ | -------------------------------- |
| `dependentName`            | string | Dependent library                |
| `dependentVersionName`     | string | Dependent version                |
| `dependentEcosystem`       | string | Ecosystem                        |
| `targetLibraryVersionName` | string | Target version being depended on |

---

# SPARQL Semantics

## Forward Dependency

```sparql
?libVersion sc:dependsOn ?dependencyVersion .
```

## Reverse Dependency

```sparql
?dependentVersion sc:dependsOn ?targetVersion .
```

## Indirect (≥2 hops)

```sparql
sc:dependsOn/sc:dependsOn+
```

## Tree Expansion Strategy

The tree API:

1. Queries direct dependencies of the root
2. Recursively queries dependencies of each child
3. Builds nested structure in application code
4. Applies depth limits, dedup, and cycle handling

---

# Error Responses

| Code | Description               |
| ---- | ------------------------- |
| 400  | Invalid parameters        |
| 404  | Library/version not found |
| 502  | SPARQL endpoint error     |

---

# Summary

| Endpoint           | Description                    |
| ------------------ | ------------------------------ |
| `/dependencies`    | Flat dependency list           |
| `/dependency-tree` | Full dependency graph (nested) |
| `/dependents`      | Reverse dependencies           |

---