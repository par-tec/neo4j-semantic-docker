import logging
import re
from time import time

import pandas as pd
import yaml
from rdflib import Graph

import kuberdf
import mermaidrdf

log = logging.getLogger(__name__)
HEADERS = ["node", "relation", "artifact", "technique"]


def initialize_graph(ontologies):
    ts = time()
    log.info("Loading ontologies..")
    g = Graph()
    g.bind("d3f", mermaidrdf.NS_D3F)
    for ontology in ontologies:
        g.parse(ontology, format="turtle")
    log.info(f"Ontologies loaded in {time()-ts}s")
    return g


def markdown_to_mermaid(text):
    mermaid_graphs = mermaidrdf.extract_mermaid(text)
    mermaid = "graph\n" + "\n".join(
        re.sub(r"^graph.*\n", "", graph) for graph in mermaid_graphs
    )
    return mermaid


def markdown_to_rdf(text):
    mermaid_graphs = mermaidrdf.extract_mermaid(text)
    turtle = ""
    for graph in mermaid_graphs:
        turtle += "\n" + mermaidrdf.parse_mermaid(graph)
    return turtle


def rdf_to_mermaid(g: Graph):
    mermaid = mermaidrdf.MermaidRDF(g)
    return mermaid.render()


def content_to_rdf(text):
    dispatch_table = {
        "mermaid": mermaidrdf.parse_mermaid,
        "kubernetes": kuberdf.parse_manifest,
        "markdown": markdown_to_rdf,
    }
    text_type = guess_content(text)
    if text_type not in dispatch_table:
        return f"Unsupported content type {text_type}"
    f = dispatch_table[text_type]
    return f(text)


def guess_content(text):
    """Guess the content type of the text: mermaid or kubernetes manifest."""
    text = text.strip()
    if text.startswith("graph"):
        # XXX: we still need to strip '---\ntitle: ...\n---'
        return "mermaid"
    if "```mermaid" in text:
        return "markdown"
    if any(("kind" in x for x in yaml.safe_load_all(text))):
        return "kubernetes"
    return None


def attack_summary(g: Graph):
    ret = list(
        g.query(
            """
        prefix : <https://par-tec.it/example#>
        prefix d3f: <http://d3fend.mitre.org/ontologies/d3fend.owl#>
        prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT
            ?node ?relation ?artifact ?attack_id ?attack_label ?attack
        WHERE {
            ?node a :Node .
            ?node ?relation ?artifact .
            ?attack d3f:attack-id ?attack_id .
            ?attack ?attacks ?artifact .
            ?attack rdfs:label ?attack_label .
            }
        """
        )
    )

    return [HEADERS] + [render_row(row) for row in ret]


def d3fend_summary(g: Graph):
    ret = list(
        g.query(
            """
        prefix : <https://par-tec.it/example#>
        prefix d3f: <http://d3fend.mitre.org/ontologies/d3fend.owl#>
        prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT
            ?node ?relation ?artifact ?d3fend_id ?d3fend_label ?d3fend
        WHERE {
            ?node a :Node .
            ?node ?relation ?artifact .
            ?d3fend d3f:d3fend-id ?d3fend_id .
            ?d3fend ?defends ?artifact .
            ?d3fend rdfs:label ?d3fend_label .
            }
        """
        )
    )

    return [HEADERS] + [render_row(row) for row in ret]


def d3fend_summary_html(g: Graph, aggregate=False):
    return f_summary_html(g, aggregate, d3fend_summary)


def attack_summary_html(g: Graph, aggregate=False):
    return f_summary_html(g, aggregate, attack_summary)


def f_summary_html(g: Graph, aggregate=False, summary_function=d3fend_summary):
    rows = summary_function(g)
    df = pd.DataFrame(data=rows[1:], columns=rows[0])
    if aggregate:
        df = df.groupby(["node", "artifact", "technique"], as_index=False).agg(",".join)
    df = df[HEADERS]
    html = df.to_html(
        formatters=[markdown_link_to_html_link] * len(HEADERS), escape=False
    )
    return html


def list_as_html_table(rows):
    html = "<table>"
    for row in rows:
        html += "<tr>"
        try:
            cells = render_row(row)
            for cell in cells:
                cell = markdown_link_to_html_link(cell)
                html += f"<td>{cell}</td>"
        except Exception as e:
            log.exception(row + " " + str(e))
        html += "</tr>"
    html += "</table>"
    return html


def markdown_link_to_html_link(markdown_link):
    if markdown_link.startswith("["):
        label, url = markdown_link[1:].split("](")
        return f'<a href="{url[:-1]}" target="_blank" rel="noopener noreferrer">{label}</a>'
    return markdown_link


def render_row(row):
    """
    https://next.d3fend.mitre.org/technique/d3f:Client-serverPayloadProfiling/
    """

    def _fix_url(url):
        url = str(url).replace("http://d3fend.mitre.org/ontologies/d3fend.owl#", "d3f:")
        url = str(url).replace("https://par-tec.it/example#", ":")
        url = str(url).replace("http://www.w3.org/1999/02/22-rdf-syntax-ns#", "rdf:")
        return url.rsplit("/", 1)[-1]

    def _get_technique_url(technique_id, technique_uri):
        if technique_id.startswith("T"):
            attack_url = technique_id.replace(".", "/")
            return f"https://attack.mitre.org/techniques/{attack_url}"
        if technique_id.startswith("D3"):
            d3fend_url = technique_uri.split("#", 1)[-1]
            return f"https://next.d3fend.mitre.org/technique/d3f:{d3fend_url}"
        raise NotImplementedError(technique_id, technique_uri)

    node, relation, artifact, technique_id, technique_label, technique_uri = row
    artifact_name = artifact.split("#")[-1]
    artifact_url = f"https://next.d3fend.mitre.org/dao/artifact/d3f:{artifact_name}"

    technique_url = _get_technique_url(technique_id, technique_uri)
    return (
        _fix_url(node),
        _fix_url(relation),
        f"[{artifact_name}]({artifact_url})",
        f"[{technique_id} - {technique_label}]({technique_url})",
    )
