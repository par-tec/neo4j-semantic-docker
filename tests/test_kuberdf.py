from pathlib import Path

import pytest
import yaml
from rdflib import Graph, URIRef

from kuberdf import DC, parse_manifest_as_graph, parse_manifests, parse_resource

TESTCASES = yaml.safe_load(
    (Path(__file__).parent / "data" / "kuberdf" / "testcases-kube.yaml").read_text()
)["testcases"]


@pytest.mark.parametrize("test_name,test_data", TESTCASES["test_service"].items())
def test_service(test_name, test_data):
    harn_parse_manifests(test_name, test_data)


@pytest.mark.parametrize("test_name,test_data", TESTCASES["test_dc"].items())
def test_dc(test_name, test_data):
    harn_parse_manifests(test_name, test_data)


def harn_parse_manifests(test_name, test_data):
    manifest = test_data["manifest"]
    expected = set(tuple(x) for x in test_data["expected"])
    g = parse_manifest_as_graph(manifest)
    triples = g.triples((None, None, None))
    actual = [tuple(map(str, x)) for x in triples]
    assert expected < set(actual)


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


def test_parse_dc():
    manifest = yaml.safe_load(
        """
    apiVersion: apps.openshift.io/v1
    kind: DeploymentConfig
    metadata:
      name: hello-world
      namespace: default
    spec:
      replicas: 1
      selector:
        app: hello-world
      template:
        metadata:
          labels:
            app: hello-world
        spec:
          containers:
          - image: quay.io/openshiftlabs/hello-world
            imagePullPolicy: Always
            name: hello-world
            ports:
            - containerPort: 8080
              protocol: TCP
            resources: {}
            terminationMessagePath: /dev/termination-log
            terminationMessagePolicy: File
          dnsPolicy: ClusterFirst
          restartPolicy: Always
          schedulerName: default-scheduler
          securityContext: {}
          terminationGracePeriodSeconds: 30
    status: {}
    """
    )
    resource = DC(manifest)
    assert resource.kind == "DeploymentConfig"
    assert resource.name == "hello-world"
    assert resource.namespace == "default"
    assert resource.triples() is not None
    assert (
        URIRef("urn:k8s:default/container/hello-world"),
        URIRef("urn:k8s:exposes"),
        URIRef("TCP://app=hello-world:8080"),
    ) in resource.triples()


def test_graph():
    manifests = Path("tests").glob("**/*.yaml")
    parse_manifests(manifests, "deleteme")
