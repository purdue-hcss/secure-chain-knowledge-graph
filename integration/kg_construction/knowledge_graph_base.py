from typing import Iterable

from knowledge_graph_constant import (
    NS,
    PROPERTY_DEPENDS_ON,
    PROPERTY_DISCOVER,
    PROPERTY_ECOSYSTEM,
    PROPERTY_HAS_HARDWARE_VERSION,
    PROPERTY_HAS_SOFTWARE_VERSION,
    PROPERTY_OPERATES_ON,
    PROPERTY_VERSION_NAME,
    PROPERTY_VULNERABILITY_TYPE,
    PROPERTY_VULNERABLE_TO,
    SCHEMA,
)
from rdflib import OWL, RDF, RDFS, BNode, Graph, Literal, URIRef
from rdflib.collection import Collection



def bind_prefixes(g: Graph):
    g.bind("schema", SCHEMA)
    g.bind("sc", NS)


def make_union_class(
    g: Graph, classes: Iterable[URIRef], label: str | None = None
) -> BNode:
    union_cls = BNode()
    class_list = BNode()

    Collection(g, class_list, list(classes))

    g.add((union_cls, RDF.type, OWL.Class))
    g.add((union_cls, OWL.unionOf, class_list))

    if label:
        g.add((union_cls, RDFS.label, Literal(label)))

    return union_cls


def add_classes(g: Graph):
    g.add((NS.Software, RDF.type, RDFS.Class))
    g.add((NS.SoftwareVersion, RDF.type, RDFS.Class))
    g.add((NS.Hardware, RDF.type, RDFS.Class))
    g.add((NS.HardwareVersion, RDF.type, RDFS.Class))
    g.add((NS.License, RDF.type, RDFS.Class))
    g.add((NS.VulnerabilityType, RDF.type, RDFS.Class))
    g.add((NS.Vulnerability, RDF.type, RDFS.Class))

    g.add((NS.Software, RDFS.subClassOf, SCHEMA.SoftwareApplication))
    g.add((NS.SoftwareVersion, RDFS.subClassOf, NS.Software))
    g.add((NS.Hardware, RDFS.subClassOf, SCHEMA.Product))
    g.add((NS.HardwareVersion, RDFS.subClassOf, NS.Hardware))
    g.add((NS.License, RDFS.subClassOf, SCHEMA.CreativeWork))
    g.add((NS.VulnerabilityType, RDFS.subClassOf, SCHEMA.Intangible))
    g.add((NS.Vulnerability, RDFS.subClassOf, SCHEMA.Intangible))


def add_ns_properties(g: Graph):
    g.add((PROPERTY_DEPENDS_ON, RDF.type, RDF.Property))
    g.add((PROPERTY_DEPENDS_ON, RDFS.domain, NS.SoftwareVersion))
    g.add((PROPERTY_DEPENDS_ON, RDFS.range, NS.SoftwareVersion))

    g.add((PROPERTY_DISCOVER, RDF.type, RDF.Property))
    discover_domain_class = make_union_class(g, [SCHEMA.Organization, SCHEMA.Person])
    g.add((PROPERTY_DISCOVER, RDFS.domain, discover_domain_class))
    g.add((PROPERTY_DISCOVER, RDFS.range, NS.Vulnerability))

    g.add((PROPERTY_HAS_HARDWARE_VERSION, RDF.type, RDF.Property))
    g.add((PROPERTY_HAS_HARDWARE_VERSION, RDFS.domain, NS.Hardware))
    g.add((PROPERTY_HAS_HARDWARE_VERSION, RDFS.range, NS.HardwareVersion))

    g.add((PROPERTY_HAS_SOFTWARE_VERSION, RDF.type, RDF.Property))
    g.add((PROPERTY_HAS_SOFTWARE_VERSION, RDFS.domain, NS.Software))
    g.add((PROPERTY_HAS_SOFTWARE_VERSION, RDFS.range, NS.SoftwareVersion))

    g.add((PROPERTY_OPERATES_ON, RDF.type, RDF.Property))
    g.add((PROPERTY_OPERATES_ON, RDFS.domain, NS.SoftwareVersion))
    g.add((PROPERTY_OPERATES_ON, RDFS.range, NS.HardwareVersion))

    g.add((PROPERTY_VULNERABILITY_TYPE, RDF.type, RDF.Property))
    g.add((PROPERTY_VULNERABILITY_TYPE, RDFS.domain, NS.Vulnerability))
    g.add((PROPERTY_VULNERABILITY_TYPE, RDFS.range, NS.VulnerabilityType))

    g.add((PROPERTY_VULNERABLE_TO, RDF.type, RDF.Property))
    g.add((PROPERTY_VULNERABLE_TO, RDFS.domain, NS.SoftwareVersion))
    g.add((PROPERTY_VULNERABLE_TO, RDFS.range, NS.Vulnerability))

    g.add((PROPERTY_VERSION_NAME, RDF.type, RDF.Property))
    versionName_domain_class = make_union_class(
        g, [NS.SoftwareVersion, NS.HardwareVersion]
    )
    g.add((PROPERTY_VERSION_NAME, RDFS.domain, versionName_domain_class))
    g.add((PROPERTY_VERSION_NAME, RDFS.range, SCHEMA.Text))

    g.add((PROPERTY_ECOSYSTEM, RDF.type, RDF.Property))
    g.add((PROPERTY_ECOSYSTEM, RDFS.domain, NS.Software))
    g.add((PROPERTY_ECOSYSTEM, RDFS.range, SCHEMA.Text))


def construct_base_graph() -> Graph:
    graph = Graph()
    bind_prefixes(graph)
    add_classes(graph)
    add_ns_properties(graph)
    return graph
