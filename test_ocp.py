from pathlib import Path

import pytest
import yaml
from rdflib import RDF, RDFS, Graph, Literal, Namespace, URIRef

NS_K8S = Namespace("urn:k8s:")


def test_graph():
    manifests = Path(".").glob("**/*.yaml")
    g = Graph()
    g.parse(data=ontology(), format="turtle")
    g.bind("k8s", NS_K8S)
    for f in manifests:
        manifest = yaml.safe_load(f.read_text())
        if "kind" not in manifest:
            continue
        for triple in parse_resource(manifest):
            g.add(triple)
    g.serialize("deleteme.ttl", format="turtle")
    g.serialize("deleteme.jsonld", format="application/ld+json")


def ontology():
    """
    A basic ontology for OpenShift
    """

    return """
    @prefix k8s: <urn:k8s:> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

    k8s:Namespace a rdfs:Class ;
        rdfs:label "Namespace" .

    k8s:connected a rdf:Property .
    k8s:hasNamespace a rdf:Property .
    k8s:hasApplication a rdf:Property;
        rdfs:subPropertyOf k8s:connected  .
    k8s:hasTarget a rdf:Property ;
        rdfs:subPropertyOf k8s:connected  .
    k8s:hasContainer a rdf:Property ;
        rdfs:subPropertyOf k8s:connected  .
    k8s:hasSelector a rdf:Property ;
        rdfs:subPropertyOf k8s:connected  .
    k8s:hasImage a rdf:Property ;
        rdfs:subPropertyOf k8s:connected  .

    # Kinds
    k8s:Kind a rdfs:Class .
    k8s:DeploymentConfig a k8s:Kind .
    k8s:Service a k8s:Kind .
    k8s:ImageStream a k8s:Kind .
    k8s:Route a k8s:Kind .
    k8s:BuildConfig a k8s:Kind .
    k8s:Container a k8s:Kind .
    k8s:Image a k8s:Kind .
    k8s:Application a k8s:Kind .
    k8s:Host a k8s:Kind .
    k8s:Port a k8s:Kind .

    """


@pytest.mark.parametrize("manifest_yaml", Path(".").glob("**/*.yaml"))
def test_parse_resource(manifest_yaml):
    """Parse an openshift manifest file
    and convert it to an RDF resource
    """
    g = Graph()
    manifest = yaml.safe_load(manifest_yaml.read_text())
    if "kind" not in manifest:
        return
    for triple in parse_resource(manifest):
        g.add(triple)

    assert g is not None


def test_parse_dc():
    g = Graph()
    for manifest_yaml in (
        Path("dati-semantic-backend/deploymentConfig.yaml"),
        Path("dati-semantic-backend/service.yaml"),
    ):
        manifest = yaml.safe_load(manifest_yaml.read_text())
        for triple in parse_resource(manifest):
            g.add(triple)

    # raise NotImplementedError


class K8Resource:
    def __init__(self, manifest=None) -> None:

        self.kind = manifest["kind"]
        self.metadata = manifest["metadata"]
        self.name = self.metadata["name"]
        self.namespace = manifest["metadata"].get("namespace", "default")
        self.ns = NS_K8S[self.namespace]
        self.spec = manifest.get("spec", {})
        self.uri = self.ns + f"/{self.kind}/{self.name}"

    def triples_ns(self):
        yield self.ns, RDF.type, NS_K8S.Namespace
        yield self.ns, RDFS.label, Literal(self.namespace)

    def triples_self(self):
        yield self.uri, RDF.type, NS_K8S[self.kind]
        yield self.uri, RDFS.label, Literal(self.name)
        yield self.uri, NS_K8S.hasNamespace, self.ns

        for k, v in self.metadata.get("labels", {}).items():
            yield self.uri, RDFS.label, Literal(f"{k}: {v}")

    def triple_spec(self):
        classmap = {
            "Route": Route.triple_spec,
            "Service": Service.triple_spec,
            "DeploymentConfig": DC.triple_spec,
            "HorizontalPodAutoscaler": dontyield,
            "ImageStreamTag": dontyield,
            "ImageStream": dontyield,
        }
        if self.spec:
            yield from classmap[self.kind](self)

    def triples(self):
        yield from self.triples_ns()
        yield from self.triples_self()
        yield from self.triple_spec()


class Route(K8Resource):
    def triple_spec(self):
        for k, v in self.spec.items():
            if k == "host":
                host_u = URIRef(f"https://{v}{self.spec.get('path', '')}")
                yield host_u, RDF.type, NS_K8S.Host
                yield host_u, NS_K8S.hasTarget, self.uri
                yield self.uri, NS_K8S.hasHost, host_u
            if k == "to":
                rel_kind = v["kind"]
                rel_name = v["name"]
                rel_port = self.spec.get("port", {}).get("targetPort")
                dport = URIRef(f"TCP://{rel_name}:{rel_port}")
                yield self.uri, NS_K8S.hasTarget, self.ns + f"/{rel_kind}/{rel_name}"
                yield self.uri, NS_K8S.hasTarget, dport
                yield dport, RDF.type, NS_K8S.Port


def dontyield(*a, **kw):
    yield from []


class Service(K8Resource):
    def triple_spec(self):
        for port in self.spec["ports"]:
            host_u = URIRef(f"http://{self.name}:{port['port']}")
            yield self.uri, NS_K8S.hasHost, host_u
            yield host_u, RDF.type, NS_K8S.Port
            if "selector" in self.spec:
                target_host = self.spec["selector"]["deploymentConfig"]
                yield host_u, NS_K8S.hasTarget, URIRef(
                    f'{port["protocol"]}://{target_host}:{port["targetPort"]}'
                )
        if selector := self.spec.get("selector"):
            yield self.uri, NS_K8S.hasSelector, self.ns + f"/DeploymentConfig/{selector['deploymentConfig']}"


class DC(K8Resource):
    def triple_spec(self):
        for k, v in self.spec.items():
            if k == "template":
                for container in v.get("spec", {}).get("containers", []):
                    s_container = self.ns + f'/container/{container["name"]}'
                    yield self.uri, NS_K8S.hasContainer, s_container
                    yield s_container, RDF.type, NS_K8S.Container

                    if "image" in container:
                        yield s_container, NS_K8S.hasImage, URIRef(container["image"])
                        yield URIRef(container["image"]), RDF.type, NS_K8S.Image

                    if "ports" in container:
                        for port in container["ports"]:
                            proto = port.get("protocol", "tcp").upper()
                            host_u = URIRef(
                                f"{proto}://{self.name}:{port['containerPort']}"
                            )
                            yield s_container, NS_K8S.hasPort, host_u
                            yield host_u, RDF.type, NS_K8S.Port

                    for env in container.get("env", []):
                        if env.get("value", "").startswith(("http://", "https://")):
                            yield URIRef(env["value"]), RDF.type, NS_K8S.Host
                            yield s_container, NS_K8S.hasTarget, URIRef(env["value"])


def parse_resource(manifest):
    """Parse an openshift manifest file
    and convert it to an RDF resource
    """
    resource = K8Resource(manifest)

    yield from resource.triples()
