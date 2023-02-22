import logging
from pathlib import Path

import pytest
import yaml
from rdflib import Graph

from mermaidrdf import MermaidRDF

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

TESTCASES = yaml.safe_load(
    (Path(__file__).parent / "data" / "mermaidrdf" / "testcases-rdf.yaml").read_text()
)["testcases"]

ICON_MAP = {
    "urn:k8s:Service": "fa:fa-network-wired",
    "urn:k8s:Port": "fa:fa-ethernet",
    "urn:k8s:Deployment": "fa:fa-cubes",
    "urn:k8s:Pod": "fa:fa-cube",
    "urn:k8s:Container": "fa:fa-cube",
    "urn:k8s:DeploymentConfig": "⟳",
    "urn:k8s:Namespace": "⬚",
    "urn:k8s:Image": "fa:fa-docker",
    "urn:k8s:Application": "fa:fa-cubes",
}


@pytest.mark.parametrize(
    "test_name,test_data", TESTCASES["test_rdf_to_mermaid"].items()
)
def test_rdf_to_mermaid(test_name, test_data):
    mermaid = test_data["turtle"]
    expected = test_data["expected"]
    g = Graph()
    g.parse(data=mermaid, format="turtle")
    mermaid = MermaidRDF(g)
    mermaid_text = mermaid.render().splitlines()
    assert set(mermaid_text) == set(expected)
