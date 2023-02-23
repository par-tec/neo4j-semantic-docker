import logging
import os
from pathlib import Path
from time import time

import pytest
import yaml
from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from kuberdf import DC, NS_K8S, parse_manifest_as_graph, parse_manifests, parse_resource
from mermaidrdf import MermaidRDF

log = logging.getLogger(__name__)


TESTCASES = yaml.safe_load(
    (Path(__file__).parent / "data" / "kuberdf" / "testcases-kube.yaml").read_text()
)["testcases"]


def test_file():
    TEST_KUBERDF_FILE = os.environ.get("TEST_KUBERDF_FILE")
    kube_yaml = Path(TEST_KUBERDF_FILE)
    assert kube_yaml.is_file()
    t0 = time()
    log.info(f"Testing {kube_yaml}")
    g = parse_manifest_as_graph(
        manifest_text=kube_yaml.read_text(), manifest_format=kube_yaml.suffix[1:]
    )
    log.info(f"Loaded {kube_yaml} in {time()-t0}s")
    assert len(g) > 1000

    x = Graph()
    # Add all g triples to x
    for s, p, o in g:
        if (p, o) == (RDF.type, NS_K8S.Namespace):
            x.add((s, p, o))
        if "ws" in f"{s}{o}":
            x.add((s, p, o))
    assert len(x) < len(g)
    # convert x to mermaid
    mermaid = MermaidRDF(x)
    mermaid_text = mermaid.render()
    mermaid_text.splitlines()

    raise NotImplementedError


@pytest.mark.parametrize("test_name,test_data", TESTCASES["test_network"].items())
def test_network(test_name, test_data):
    harn_parse_manifests(test_name, test_data)


@pytest.mark.parametrize("test_name,test_data", TESTCASES["test_service"].items())
def test_service(test_name, test_data):
    harn_parse_manifests(test_name, test_data)


@pytest.mark.parametrize("test_name,test_data", TESTCASES["test_dc"].items())
def test_dc(test_name, test_data):
    harn_parse_manifests(test_name, test_data)


@pytest.mark.parametrize("test_name,test_data", TESTCASES["test_list"].items())
def test_list(test_name, test_data):
    harn_parse_manifests(test_name, test_data)


@pytest.mark.parametrize("test_name,test_data", TESTCASES["test_skip"].items())
def test_skip(test_name, test_data):
    actual = harn_parse_manifests(test_name, test_data)
    assert actual == []


def harn_parse_manifests(test_name, test_data):
    manifest = test_data["manifest"]
    expected = set(tuple(x) for x in test_data["expected"])
    g = parse_manifest_as_graph(manifest)
    triples = g.triples((None, None, None))
    actual = [tuple(map(str, x)) for x in triples]
    assert expected <= set(actual)
    return actual


@pytest.mark.parametrize("manifest_yaml", Path(".").glob("**/kuberdf/*.yaml"))
def test_parse_resource(manifest_yaml):
    """Parse an openshift manifest file
    and convert it to an RDF resource
    """
    g = Graph()
    manifests = yaml.safe_load_all(manifest_yaml.read_text())
    for manifest in manifests:
        if "kind" not in manifest:
            return
        for triple in parse_resource(manifest):
            g.add(triple)

    assert g is not None


def test_graph():
    manifests = Path("tests").glob("**/*.yaml")
    parse_manifests(manifests, "deleteme")


@pytest.mark.parametrize(
    "image",
    [
        "image-registry.openshift-image-registry.svc:5000/foo-foo/bar-bars",
        "image-registry.openshift-image-registry.svc:5000/foo-foo/bar-bar@sha256:fafafa",
        "alpine",
        "library/alpine",
        "docker.io/library/alpine",
    ],
)
def test_image(image):
    g = Graph()
    for triple in DC.parse_image(image, URIRef("urn:k8s:Container/uri")):
        g.add(triple)

    assert g.serialize() is None
    raise NotImplementedError
