import json
import logging
from pathlib import Path
from time import time
from urllib.parse import urlparse

import yaml
from rdflib import RDF, RDFS, Graph, Literal, Namespace, URIRef

log = logging.getLogger(__name__)
NS_K8S = Namespace("urn:k8s:")


def dontyield(*a, **kw):
    yield from []


skip_resource_instances = dontyield


def strip_oci_image_tag(image: str) -> str:
    """Strip the tag from an OCI image name"""
    return image.rsplit(":")[0].split("@sha256", 1)[0]


def parse_manifests(
    manifests: Path, outfile: str, ns_from_file=False, jsonld_output=False
):
    g = Graph()
    g.parse(data=(Path(__file__).parent / "ontology.ttl").read_text(), format="turtle")
    g.bind("k8s", NS_K8S)
    for f in manifests:
        ns = f.stem if ns_from_file else None
        log.info(f"Parsing {f} with namespace {ns}")
        parse_manifest_as_graph(f.read_text(), g=g, manifest_format=f.suffix[1:])
    outfile = Path(outfile)
    g.serialize(outfile.with_suffix(".ttl").as_posix(), format="turtle")
    if jsonld_output:
        g.serialize(
            outfile.with_suffix(".jsonld").as_posix(), format="application/ld+json"
        )


def parse_manifest(manifest_text: str) -> str:
    """Parse a manifest text and return a list of triples"""
    g = parse_manifest_as_graph(manifest_text)
    return g.serialize(format="turtle")


def parse_manifest_as_graph(
    manifest_text: str, manifest_format="yaml", g=None
) -> Graph:
    """Parse a manifest text and return a list of triples.
    If a graph is provided, the triples will be added to it,
    otherwise a new graph will be created.
    """

    def _json_loads_array(json_text):
        return (json.loads(json_text),)

    ts = time()
    log.info(f"Reading manifest with format {manifest_format}")
    manifest_text = manifest_text.strip()
    if manifest_format == "yaml":
        parser_f = yaml.safe_load_all
    elif manifest_format == "json" or manifest_text[0] == "{":
        parser_f = _json_loads_array
    else:
        raise ValueError(f"Unknown manifest format: {manifest_format}")
    log.warning(f"Read manifest in %d Using parser {parser_f}", (time() - ts))
    g = g or Graph()
    g.bind("k8s", NS_K8S)
    for manifest in parser_f(manifest_text):
        if "kind" not in manifest:
            continue
        for triple in parse_resource(manifest):
            g.add(triple)
    return g


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


class SkipResource:
    def __init__(self, *a, **k):
        pass

    def triples(self):
        yield from []


class K8Resource:
    @staticmethod
    def factory(manifest, ns=None):
        classmap = {
            "BuildConfig": BuildConfig,
            "ConsolePlugin": None,
            "Deployment": DC,
            "DeploymentConfig": DC,
            "Endpoints": None,
            "HorizontalPodAutoscaler": None,
            "ImageStream": None,
            "ImageStreamTag": None,
            "Job": SkipResource,
            "List": K8List,
            "Pod": SkipResource,
            "ReplicationController": ReplicationController,
            "Route": Route,
            "Service": Service,
        }
        kind = manifest.get("kind")
        clz = classmap.get(kind) or K8Resource
        return clz(manifest, ns=ns)

    def get_app_uri(self, metadata):
        app = metadata.get("labels", {}).get("app")
        return URIRef(self.ns + f"/Application/{app}") if app else None

    def __init__(self, manifest=None, ns: str = None) -> None:
        if ":" in str(ns):
            raise ValueError(f"Invalid namespace: {ns}")
        self.kind = manifest["kind"]
        self.metadata = manifest["metadata"]
        self.name = self.metadata["name"]
        self.namespace = manifest["metadata"].get("namespace", ns or "default")
        self.ns = NS_K8S[self.namespace]
        self.spec = manifest.get("spec", {})
        if self.kind == "Namespace":
            self.uri = self.ns
        else:
            self.uri = self.ns + f"/{self.kind}/{self.name}"

        # Set the application.
        self.app = self.get_app_uri(self.metadata)

    def triples_kind(self):
        yield (NS_K8S[self.kind], RDF.type, NS_K8S.Kind)

    def triples_ns(self):
        yield self.ns, RDF.type, NS_K8S.Namespace
        yield self.ns, RDFS.label, Literal(self.namespace)
        yield NS_K8S.cluster, NS_K8S.hasChild, self.ns

    def triples_self(self):
        yield self.uri, RDF.type, NS_K8S[self.kind]
        yield self.uri, NS_K8S.hasNamespace, self.ns
        yield self.ns, NS_K8S.hasChild, self.uri
        yield self.uri, RDFS.label, Literal(self.label)

        for k, v in self.metadata.get("labels", {}).items():
            yield self.uri, RDFS.label, Literal(f"{k}: {v}")
        if self.app:
            yield self.ns, NS_K8S.hasChild, self.app
            yield self.app, RDF.type, NS_K8S.Application
            yield self.app, NS_K8S.hasChild, self.uri

    def triple_spec(self):
        yield from []

    @property
    def label(self):
        labelmap = {
            "BuildConfig": "bc",
            "Deployment": "dc",
            "DeploymentConfig": "dc",
            "ImageStream": "is",
            "ImageStreamTag": "ist",
            "Namespace": "ns",
            "PersistentVolumeClaim": "pvc",
            "Route": "route",
            "Service": "svc",
        }
        if self.kind in labelmap:
            return f"{labelmap[self.kind]}/{self.name}"
        return f"{self.kind}:{self.name}"

    def _triple_spec(self):
        classmap = {
            "ConsolePlugin": dontyield,
            "Deployment": DC.triple_spec,
            "DeploymentConfig": DC.triple_spec,
            "Endpoints": dontyield,
            "HorizontalPodAutoscaler": dontyield,
            "ImageStream": skip_resource_instances,
            "ImageStreamTag": dontyield,
            "Pod": skip_resource_instances,
            "ReplicationController": dontyield,
            "Job": skip_resource_instances,
            "Route": Route.triple_spec,
            "Service": Service.triple_spec,
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
                host_u = URIRef(f"TCP://{v}{self.spec.get('path', '')}:443")
                yield host_u, RDF.type, NS_K8S.Host
                yield host_u, NS_K8S.accesses, self.uri
                yield self.uri, NS_K8S.hasHost, host_u
                yield host_u, NS_K8S.hasNamespace, self.ns
                if self.ns:  # FIXME: Add tests
                    yield self.ns, NS_K8S.hasChild, host_u
                yield self.ns, NS_K8S.hasChild, host_u

            if k == "to":
                rel_kind = v["kind"]
                rel_name = v["name"]
                yield self.uri, NS_K8S.accesses, self.ns + f"/{rel_kind}/{rel_name}"
                # yield self.ns + f"/{rel_kind}/{rel_name}", RDF.type, NS_K8S[rel_kind]
                # rel_port = self.spec.get("port", {}).get("targetPort")
                # dport = URIRef(f"TCP://{rel_name}:{rel_port}")
                # yield self.uri, NS_K8S.hasTarget, dport
                # yield dport, RDF.type, NS_K8S.Port


class Service(K8Resource):
    def triple_spec(self):
        # Get externalname host or ip
        if external_name := self.spec.get("externalName"):
            # ExternalName can cause troubles.
            # see https://kubernetes.io/docs/concepts/services-networking/service/#externalname
            host_u = URIRef(f"fixme://{external_name}")

            yield host_u, RDF.type, NS_K8S.Host
            yield host_u, NS_K8S.accesses, self.uri
            yield self.uri, NS_K8S.hasHost, host_u

        for port in self.spec.get("ports", []):
            host_u = URIRef(f"{port['protocol']}://{self.name}:{port['port']}")
            yield self.uri, NS_K8S.hasHost, host_u
            yield host_u, RDF.type, NS_K8S.Host
            yield self.uri, NS_K8S.Port, Literal(
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
    @staticmethod
    def parse_image(image, container_uri=None):
        image_url_type = len(image.split("/"))
        if image_url_type == 1:  # only image name
            image = "https://docker.io/library/" + image
        elif image_url_type == 2:  # image name and organization
            image = "https://docker.io/" + image
        elif image_url_type == 3:  # image name, organization and registry
            image = "https://" + image
        else:
            pass

        image_url = urlparse(image)
        image_uri = URIRef(
            image_url._replace(path=strip_oci_image_tag(image_url.path)).geturl()
        )
        if image_url.netloc:
            yield URIRef(image_url.netloc), RDF.type, NS_K8S.Registry
            yield URIRef(image_url.netloc), NS_K8S.hasChild, image_uri

        yield image_uri, RDF.type, NS_K8S.Image
        if container_uri:
            yield container_uri, NS_K8S.hasImage, image_uri

    def triple_spec(self):
        if not (template := self.spec.get("template")):
            return
        containers = template.get("spec", {}).get("containers", [])
        volumes = template.get("spec", {}).get("volumes", [])
        metadata = template.get("metadata", {})
        template_labels = metadata.get("labels", {})
        template_app = self.get_app_uri(metadata) or self.app
        for volume in volumes:
            if "persistentVolumeClaim" in volume:
                pvc = volume["persistentVolumeClaim"]["claimName"]
                s_volume = self.ns + f"/PersistentVolumeClaim/{pvc}"
                yield self.uri, NS_K8S.hasVolume, s_volume
                yield self.uri, NS_K8S.accesses, s_volume
                yield s_volume, RDF.type, NS_K8S.PersistentVolumeClaim
                # XXX: the volume can be mounted in multiple applications.
                if template_app:
                    yield template_app, NS_K8S.hasChild, s_volume
            elif "secret" in volume:
                secret = volume["secret"]["secretName"]
                s_volume = self.ns + f"/Secret/{secret}"
                yield self.uri, NS_K8S.hasVolume, s_volume
                yield self.uri, NS_K8S.accesses, s_volume
                yield s_volume, RDF.type, NS_K8S.Secret
            elif "configMap" in volume:
                configmap = volume["configMap"]["name"]
                s_volume = self.ns + f"/ConfigMap/{configmap}"
                yield self.uri, NS_K8S.hasVolume, s_volume
                yield self.uri, NS_K8S.accesses, s_volume
                yield s_volume, RDF.type, NS_K8S.ConfigMap
            elif "hostPath" in volume:
                if self.namespace.startswith(("kube-system", "openshift-", "rook-")):
                    # Ignore hostPath volumes in kube-system
                    continue
                raise NotImplementedError
            elif "emptyDir" in volume:
                # Ignore emptyDir volumes
                continue
            else:
                # """
                # TODO: {'name': 'console-serving-cert',
                #  'secret': {'defaultMode': 420, 'secretName': 'console-serving-cert'}}
                #
                # """
                raise NotImplementedError(volume)

        for container in containers:
            s_container = self.uri + f'/Container/{container["name"]}'
            yield self.uri, NS_K8S.executes, s_container
            yield s_container, RDF.type, NS_K8S.Container
            yield s_container, RDFS.label, Literal(container["name"])
            yield self.uri, NS_K8S.hasChild, s_container
            if self.app:
                yield self.app, NS_K8S.hasChild, s_container

            if "image" in container:
                yield from DC.parse_image(container["image"], container_uri=s_container)

            if "ports" in container:
                for port in container["ports"]:
                    protocol = port.get("protocol", "tcp").upper()
                    for k, v in template_labels.items():
                        port_u = URIRef(f"{protocol}://{k}={v}:{port['containerPort']}")
                        yield s_container, NS_K8S.exposes, port_u
                        yield port_u, RDF.type, NS_K8S.Port
                        if template_app:
                            yield template_app, NS_K8S.hasChild, port_u

            for env in container.get("env", []):
                try:
                    host_u = parse_url(env["value"])
                    if "." in host_u:
                        host_u = URIRef(f"TCP://{host_u}")
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


def parse_resource(manifest: dict, ns=None) -> K8Resource:
    """Parse an openshift manifest file
    and convert it to an RDF resource
    """
    resource = K8Resource.factory(manifest, ns=ns)
    try:
        if resource.namespace.startswith(("kube-system", "openshift-")):
            # Ignore kube-system and openshift- namespaces
            return
    except AttributeError:
        pass
    yield from resource.triples()


class K8List(K8Resource):
    def __init__(self, manifest=None, ns: str = None) -> None:
        """A List is a special resource, don't call super.__init__"""
        self.kind = manifest["kind"]
        self.metadata = manifest["metadata"]
        self.namespace = manifest["metadata"].get("namespace", ns or "default")
        self.ns = NS_K8S[self.namespace]
        self.spec = manifest.get("spec", {})
        self.items = manifest["items"]
        # Set the application.
        self.app = self.get_app_uri(self.metadata)

    def triples(self):
        for item in self.items:
            yield from parse_resource(item, ns=self.namespace)


class ReplicationController(DC):
    def triples(self):
        # OCP ReplicationController is created by a DeploymentConfig.
        if self.metadata.get("annotations", {}).get(
            "openshift.io/deployment-config.name"
        ):
            return
        # A real ReplicationController.
        yield from super().triples()


class BuildConfig(K8Resource):
    def triple_spec(self):
        from_image_url = None
        to_image_url = None

        to_ = self.spec.get("output", {}).get("to", {})
        if to_.get("kind") == "ImageStreamTag":
            to_image_url = URIRef(
                self.ns + "/ImageStreamTag/" + strip_oci_image_tag(to_["name"])
            )
            yield self.uri, NS_K8S.writes, to_image_url
            yield to_image_url, RDF.type, NS_K8S.ImageStreamTag

        from_ = self.spec.get("strategy", {}).get("sourceStrategy", {}).get("from", {})
        if from_.get("kind") == "ImageStreamTag":
            ns = from_.get("namespace", self.ns)
            from_image_url = URIRef(
                ns + "/ImageStreamTag/" + strip_oci_image_tag(from_["name"])
            )
            yield self.uri, NS_K8S.reads, from_image_url
            yield from_image_url, RDF.type, NS_K8S.ImageStreamTag
        if from_image_url and to_image_url:
            yield to_image_url, RDFS.subClassOf, from_image_url
