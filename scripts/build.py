import shutil

from rdflib import Graph  # pip install rdflib pyld


def shorten_d3fend():
    g = Graph()
    g.parse("https://next.d3fend.mitre.org/ontologies/d3fend.ttl")
    subset = tuple(
        g.query(
            f"CONSTRUCT {{ ?s ?p ?q . }}  WHERE {{ ?s rdfs:subClassOf* d3f:{rdf_type}; ?p ?q . }}"
        )
        for rdf_type in ("DigitalArtifact", "DefensiveTechnique", "OffensiveTechnique")
    )
    sg = Graph()
    [sg.add(t) for x in subset for t in x]
    sg.serialize("docs/mermaid/d3fend-short.ttl")


if __name__ == "__main__":

    FILES = (
        {"src": "kuberdf/__init__.py", "dst": "docs/mermaid/kuberdf.py"},
        {"src": "kuberdf/ontology.ttl", "dst": "docs/mermaid/ontology.ttl"},
        {"src": "mermaidrdf/__init__.py", "dst": "docs/mermaid/mermaidrdf.py"},
        {"src": "mermaidrdf/mermaidrdf.yaml", "dst": "docs/mermaid/mermaidrdf.yaml"},
    )
    for f in FILES:
        shutil.copy(f["src"], f["dst"])
    shorten_d3fend()
