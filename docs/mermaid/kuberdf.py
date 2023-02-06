from pathlib import Path
from urllib.parse import urlparse

import yaml
from rdflib import RDF, RDFS, Graph, Literal, Namespace, URIRef

NS_K8S = Namespace("urn:k8s:")


def parse_manifests(manifests: Path, outfile: str):
    g = Graph()
    g.parse(data=(Path(__file__).parent / "ontology.ttl").read_text(), format="turtle")
    g.bind("k8s", NS_K8S)
    for f in manifests:
        for manifest in yaml.safe_load_all(f.read_text()):
            if "kind" not in manifest:
                continue
            for triple in parse_resource(manifest):
                g.add(triple)
    g.serialize(f"{outfile}.ttl", format="turtle")
    g.serialize(f"{outfile}.jsonld", format="application/ld+json")


def parse_manifest(manifest_text: str):
    """Parse a manifest text and return a list of triples"""
    g = Graph()
    g.bind("k8s", NS_K8S)
    for manifest in yaml.safe_load_all(manifest_text):
        if "kind" not in manifest:
            continue
        for triple in parse_resource(manifest):
            g.add(triple)
    return g.serialize(format="turtle")


def parse_url(url):
    url = url.strip("jdbc:")
    if "//" not in url:
        raise ValueError(f"Invalid URL: {url}")
    u = urlparse(url)
    if ":" not in u.netloc:
        if u.scheme == "mysql":
            u = u._replace(netloc=f"{u.netloc}:3306")
        elif u.scheme == "http":
            u = u._replace(netloc=f"{u.netloc}:80")
        elif u.scheme == "https":
            u = u._replace(netloc=f"{u.netloc}:443")
    return u.netloc


class K8Resource:
    @staticmethod
    def factory(manifest):
        classmap = {
            "Route": Route,
            "Service": Service,
            "DeploymentConfig": DC,
            "Deployment": DC,
            "HorizontalPodAutoscaler": None,
            "ImageStreamTag": None,
            "ImageStream": None,
            "Endpoints": None,
            "ConsolePlugin": None,
        }
        kind = manifest.get("kind")
        if clz := classmap.get(kind):
            return clz(manifest)
        return K8Resource(manifest)

    def __init__(self, manifest=None) -> None:

        self.kind = manifest["kind"]
        self.metadata = manifest["metadata"]
        self.name = self.metadata["name"]
        self.namespace = manifest["metadata"].get("namespace", "default")
        self.ns = NS_K8S[self.namespace]
        self.spec = manifest.get("spec", {})
        if self.kind == "Namespace":
            self.uri = self.ns
        else:
            self.uri = self.ns + f"/{self.kind}/{self.name}"

    def triples_kind(self):
        yield (NS_K8S[self.kind], RDF.type, NS_K8S.Kind)

    def triples_ns(self):
        yield self.ns, RDF.type, NS_K8S.Namespace
        yield self.ns, RDFS.label, Literal(self.namespace)

    def triples_self(self):
        yield self.uri, RDF.type, NS_K8S[self.kind]
        yield self.uri, NS_K8S.hasNamespace, self.ns
        yield self.uri, RDFS.label, Literal(self.label)

        for k, v in self.metadata.get("labels", {}).items():
            yield self.uri, RDFS.label, Literal(f"{k}: {v}")

    def triple_spec(self):
        yield from []

    @property
    def label(self):
        labelmap = {
            "Deployment": "dc",
            "DeploymentConfig": "dc",
            "ImageStream": "is",
            "Namespace": "ns",
            "Service": "svc",
            "Route": "route",
            "BuildConfig": "bc",
        }
        if self.kind in labelmap:
            return f"{labelmap[self.kind]}/{self.name}"
        return f"{self.kind}:{self.name}"

    def _triple_spec(self):
        classmap = {
            "Route": Route.triple_spec,
            "Service": Service.triple_spec,
            "DeploymentConfig": DC.triple_spec,
            "Deployment": DC.triple_spec,
            "HorizontalPodAutoscaler": dontyield,
            "ImageStreamTag": dontyield,
            "ImageStream": dontyield,
            "Endpoints": dontyield,
            "ConsolePlugin": dontyield,
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
                host_u = URIRef(f"https://{v}{self.spec.get('path', '')}:443")
                yield host_u, RDF.type, NS_K8S.Host
                yield host_u, NS_K8S.accesses, self.uri
                yield self.uri, NS_K8S.hasHost, host_u
            if k == "to":
                rel_kind = v["kind"]
                rel_name = v["name"]
                yield self.uri, NS_K8S.accesses, self.ns + f"/{rel_kind}/{rel_name}"
                # yield self.ns + f"/{rel_kind}/{rel_name}", RDF.type, NS_K8S[rel_kind]
                # rel_port = self.spec.get("port", {}).get("targetPort")
                # dport = URIRef(f"TCP://{rel_name}:{rel_port}")
                # yield self.uri, NS_K8S.hasTarget, dport
                # yield dport, RDF.type, NS_K8S.Port


def dontyield(*a, **kw):
    yield from []


class Service(K8Resource):
    def triple_spec(self):
        for port in self.spec["ports"]:
            host_u = URIRef(f"{port['protocol']}://{self.name}:{port['port']}")
            yield self.uri, NS_K8S.hasHost, host_u
            yield host_u, RDF.type, NS_K8S.Host
            yield self.uri, NS_K8S.port, Literal(
                "{port}-{protocol}>{targetPort}".format(**port)
            )
            service_port = self.uri + f":{port['port']}"
            yield self.uri, NS_K8S.hasPort, service_port
            yield service_port, RDF.type, NS_K8S.Host

            if selector := self.spec.get("selector"):
                k, v = next(iter(selector.items()))
                port_u = URIRef(f"{{protocol}}://{k}={v}:{{targetPort}}".format(**port))
                yield self.uri, NS_K8S.accesses, port_u
            else:
                # yield an Endpoint with the same name as the service
                # and on the default namespace.
                endpoint_u = URIRef(f"urn:k8s:default/Endpoints/{self.name}")
                yield self.uri, NS_K8S.accesses, endpoint_u


class DC(K8Resource):
    def triple_spec(self):
        if not (template := self.spec.get("template")):
            return
        if not (containers := template.get("spec", {}).get("containers")):
            return
        template_labels = template.get("metadata", {}).get("labels", {})
        for container in containers:
            s_container = self.ns + f'/container/{container["name"]}'
            yield self.uri, NS_K8S.executes, s_container
            yield s_container, RDF.type, NS_K8S.Container
            yield s_container, RDFS.label, Literal(container["name"])

            if "image" in container:
                yield s_container, NS_K8S.hasImage, URIRef(container["image"])
                yield URIRef(container["image"]), RDF.type, NS_K8S.Image

            if "ports" in container:
                for port in container["ports"]:
                    protocol = port.get("protocol", "tcp").upper()
                    for k, v in template_labels.items():
                        port_u = URIRef(f"{protocol}://{k}={v}:{port['containerPort']}")
                        yield s_container, NS_K8S.exposes, port_u
                        yield port_u, RDF.type, NS_K8S.Port

            for env in container.get("env", []):
                try:
                    host_u = parse_url(env["value"])
                    if "." in host_u:
                        host_u = URIRef(f"https://{host_u}")
                    else:
                        # host_u is the name of a kubernetes service
                        host_u = self.ns + f"/Service/{host_u}"

                    yield host_u, RDF.type, NS_K8S.Host
                    yield s_container, NS_K8S.accesses, host_u
                except (
                    KeyError,
                    AttributeError,
                    ValueError,  # parse_url
                ):
                    pass


def parse_resource(manifest: dict) -> K8Resource:
    """Parse an openshift manifest file
    and convert it to an RDF resource
    """
    resource = K8Resource.factory(manifest)

    yield from resource.triples()
