from pathlib import Path

import pytest
import yaml
from rdflib import Graph, URIRef

from kuberdf import DC, Service, parse_manifests, parse_resource


@pytest.mark.parametrize("manifest_yaml", Path(".").glob("**/*.yaml"))
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


def test_parse_service_2():
    manifest = yaml.safe_load(
        """
        apiVersion: v1
        kind: Service
        metadata:
            name: mysql-dev-external-service
            namespace: ndc-dev
        spec:
            ports:
              - protocol: TCP
                port: 3306
                targetPort: 3306
        """
    )
    resource = Service(manifest)
    assert resource.kind == "Service"
    assert resource.name == "mysql-dev-external-service"
    assert resource.namespace == "ndc-dev"
    triples = list(resource.triples())

    assert triples
    assert (
        URIRef("urn:k8s:ndc-dev/Service/mysql-dev-external-service"),
        URIRef("urn:k8s:accesses"),
        URIRef("urn:k8s:default/Endpoints/mysql-dev-external-service"),
    ) in triples


def test_parse_service():
    manifest = yaml.safe_load(
        """
    apiVersion: v1
    kind: Service
    metadata:
      name: hello-world
      namespace: default
    spec:
      ports:
      - name: http
        port: 80
        protocol: TCP
        targetPort: 8080
      selector:
        app: hello-world
      sessionAffinity: None
      type: ClusterIP
    status:
      loadBalancer: {}
    """
    )
    resource = Service(manifest)
    assert resource.kind == "Service"
    assert resource.name == "hello-world"
    assert resource.namespace == "default"
    triples = list(resource.triples())
    assert triples
    assert (
        URIRef("urn:k8s:default/Service/hello-world"),
        URIRef("urn:k8s:hasPort"),
        URIRef("urn:k8s:default/Service/hello-world:80"),
    ) in triples


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
