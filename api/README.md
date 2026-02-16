# Dependency Query API

A RESTful API for querying software dependencies from an RDF knowledge graph using SPARQL.
The API supports:

* Flat dependency queries (direct or indirect)
* Full nested dependency tree queries
* Optional ecosystem filtering
* Depth-aware dependency traversal

---

## Base URL

```
http://<host>:<port>
```

Example:

```
http://localhost:8000
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

```bash
curl "http://localhost:8000/dependencies?library_name=ffmpeg&library_version=4.2.1"
```

### Indirect dependencies

```bash
curl "http://localhost:8000/dependencies?library_name=ffmpeg&library_version=4.2.1&transitive=true"
```

---

## Response Format

```json
{
  "libraryName": "ffmpeg",
  "libraryVersionName": "4.2.1",
  "ecosystemFilter": "Conan",
  "transitive": false,
  "ecosystem": "Conan",
  "count": 2,
  "dependencies": [
    {
      "dependencyName": "zlib",
      "dependencyVersionName": "1.2.13",
      "dependencyEcosystem": "Conan"
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

```bash
curl "http://localhost:8000/dependency-tree?library_name=ffmpeg&library_version=4.2.1"
```

---

## Response Format

```json
{
  "libraryName": "ffmpeg",
  "libraryVersionName": "4.2.1",
  "ecosystemFilter": "Conan",
  "maxDepth": 3,
  "includeRoot": true,
  "dedupStrategy": "by_version",
  "cycleStrategy": "cut",
  "nodeCount": 5,
  "tree": {
    "name": "ffmpeg",
    "version": "4.2.1",
    "ecosystem": "Conan",
    "depth": 0,
    "children": [
      {
        "name": "zlib",
        "version": "1.2.13",
        "ecosystem": "Conan",
        "depth": 1,
        "children": [
          {
            "name": "miniz",
            "version": "3.0.0",
            "ecosystem": "Conan",
            "depth": 2,
            "children": []
          }
        ]
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

# SPARQL Semantics

## Direct Dependency Pattern

```sparql
?libVersion sc:dependsOn ?dependencyVersion .
```

## Indirect-Only Pattern

```sparql
?libVersion sc:dependsOn/sc:dependsOn+ ?dependencyVersion .
```

## Tree Expansion Strategy

The tree API:

1. Queries direct dependencies of the root
2. Recursively queries dependencies of each child
3. Builds nested structure in application code
4. Applies depth limits, dedup, and cycle handling

---

# Error Responses

### 400 Bad Request

Invalid parameters.

### 404 Not Found

Root library/version not found or ecosystem mismatch.

### 502 Bad Gateway

SPARQL endpoint failure.

---

# Summary

| Endpoint           | Purpose                      | Output                      |
| ------------------ | ---------------------------- | --------------------------- |
| `/dependencies`    | Flat dependency list         | Direct or indirect only     |
| `/dependency-tree` | Full nested dependency graph | All dependencies with depth |
