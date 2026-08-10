# ⛓️ SecureChain: A Knowledge Graph for Software Supply Chain Security

Welcome to the **SecureChain** project! This repository contains the tools and scripts to build a comprehensive knowledge graph for tracking dependencies, vulnerabilities, and other critical information across the software supply chain.

## 🚀 TL;DR

**SecureChain** is a project that builds a cross-ecosystem knowledge graph (KG) of **software, hardware, and known vulnerabilities (CVE/CWE)**, linking versions, dependency edges, vendors, and advisories across sources such as ConanCenter, Debian, GitHub, deps.dev, NVD (CVE), CPE, Wikipedia/DBpedia lookups, and curated vendor info.

* **Ontology:** [Secure Chain Ontology](https://purdue-hcss.github.io/secure-chain-ontology/) (`sc:` → `https://w3id.org/secure-chain/`, extends `schema.org`)

### 🗺️ Start here (choose your path)

* **💾 I just want the data / to query it:** see **[`kg/README.md`](kg/)**
  → Links to the Google Drive data dump, public SPARQL endpoint, and example queries.

* **🛠️ I want to build or extend the KG:** see **[`integration/README.md`](integration/)**
  → End-to-end pipeline: structured data collectors, optional NER/LLM relation extraction, and KG construction scripts.

* **🎨 I want a visual query helper:** see **[`visualization/README.md`](visualization/)**
  → Blockly-based SPARQL blocks to explore the graph visually.

* **🤖 I care about AI/ML supply-chain vulnerabilities:** see **[`aisecurechain/`](https://github.com/magic-YuanTian/AISecureChain)**
  → A companion knowledge graph covering AI-specific threats (prompt injection, model poisoning, agent misuse, …) extracted from advisories and threat intel with an LLM pipeline.

* **📜 I want schema details:** see the **[ontology docs](https://purdue-hcss.github.io/secure-chain-ontology/)**
  → Full class/property hierarchy, with links to schema.org and other reused vocabularies.

## 🔗 What is the Software Supply Chain?

Software has become an integral part of crucial infrastructures throughout the United States. Underlying modern software systems is the supply chain of open-source software components, such as Apache Spark, whose functionalities are reused and integrated into various systems underpinning modern society.

![Software Supply Chain](https://purdue-hcss.github.io/nsf-software-supply-chain_security/images/image6.png)

## ⚠️ Risks in Software Supply Chains

While software supply chains empower the rapid development of software systems, they also increase the risks, since any bugs, vulnerabilities, and unauthorized changes in upstream components can propagate to downstream systems and cause severe consequences. This is evident through many software crises witnessed in recent years, such as the [Heartbleed bug](https://heartbleed.com/), the [Equifax data breach](https://www.securityweek.com/equifax-confirms-apache-struts-flaw-used-hack/#:~:text=U.S.%20credit%20reporting%20agency%20Equifax,used%20to%20breach%20its%20systems.), and the [NPM left-pad incident](https://qz.com/646467/how-one-programmer-broke-the-internet-by-deleting-a-tiny-piece-of-code) that almost broke the Internet.

## ✅ Our Solution

> Develop a unified knowledge graph to continually collect and track software dependency and vulnerabilities discussed in various online documents. 🔮

In this project, our team aims to develop a unified knowledge graph that captures rich, up-to-date information about software components in heterogeneous software ecosystems. The resulting knowledge graph will empower us to further develop a novel multi-modal query interface for knowledge dissemination, as well as new risk mitigation approaches that perform deep scans on software systems, detect potential risks, and automatically repair them.

The figure below demonstrates an example knowledge graph for software supply chain security, where each entity—such as a software library or a vulnerability—is represented as a node, and the relations between them are depicted as edges.

![Knowledge Graph Ontology](https://purdue-hcss.github.io/nsf-software-supply-chain_security/images/image11.png)

## ⛓️ Secure Chain

**SecureChain** is a project that builds a cross-ecosystem knowledge graph (KG) of **software, hardware, and known vulnerabilities (CVE/CWE)**, linking versions, dependency edges, vendors, and advisories across sources such as ConanCenter, Debian, GitHub, deps.dev, NVD (CVE), CPE, Wikipedia/DBpedia lookups, and curated vendor info.

The knowledge graph canonically uses the namespace `https://w3id.org/secure-chain/` and extends `schema.org` with a small set of classes & properties for supply-chain security.

## 🤖 AISecureChain: the AI/ML Arm

**[AISecureChain](https://github.com/magic-YuanTian/AISecureChain)** (included here as the [`aisecurechain/`](aisecurechain/) submodule) extends the SecureChain effort to the **AI/ML supply chain**. While SecureChain answers *what depends on what, and which of it is vulnerable* across conventional ecosystems, AISecureChain covers the part that classic dependency analysis cannot reach — prompt injection, model poisoning, agent misuse and similar failures, where the vulnerability lives in model behaviour and the evidence exists only as narrative text.

It crawls CVE records, vendor advisories and threat-intel feeds, uses an LLM to extract entities and relations against a fixed ontology built around the causal chain `Attack → Vulnerability → Impact`, and serves the result through REST and SPARQL APIs with a React front end. A [live demo](http://18.207.218.62:3508/) is available.

## 📂 Repository Structure

This project is organized into several key directories. For detailed information on each component, please refer to the `README.md` file within the respective directory.

```
└── SecureChain/
    ├── aisecurechain/
    ├── integration/
    ├── kg/
    └── visualization/
```

  * **[`integration/`](integration/):** Contains the complete data integration pipeline for extracting, processing, and constructing the knowledge graph.

  * **[`kg/`](kg/):** Provides access to the knowledge graph data dumps, a live SPARQL endpoint, query examples, and detailed ontology information.

  * **[`visualization/`](visualization/):** Includes a web-based tool for visualizing SPARQL queries against the knowledge graph, making it easier to explore and understand the data.

  * **[`aisecurechain/`](aisecurechain/):** A submodule tracking [AISecureChain](https://github.com/magic-YuanTian/AISecureChain), a knowledge graph of AI/ML supply-chain vulnerabilities — the AI counterpart to this repository.

# 🙌 Contributing

Contributions are welcome! Typical areas:

- New data bridges (ecosystems, registries, SBOMs)

- Schema refinements (properties/classes)

- Data quality checks & deduplication

- Query examples & dashboards

Please open an issue or PR with a clear description and steps to reproduce your changes.

# 📄 License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for more details.
