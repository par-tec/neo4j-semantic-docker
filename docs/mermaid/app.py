import logging
from time import time

import pandas as pd
import yaml
from rdflib import Graph

import kuberdf
import mermaidrdf

log = logging.getLogger(__name__)
HEADERS = ["node", "relation", "artifact", "attack"]


def initialize_graph(ontologies):
    ts = time()
    log.info("Loading ontologies..")
    g = Graph()
    for ontology in ontologies:
        g.parse(ontology, format="turtle")
    log.info(f"Ontologies loaded in {time()-ts}s")
    return g


def content_to_rdf(text):
    dispatch_table = {
        "mermaid": mermaidrdf.parse_mermaid,
        "kubernetes": kuberdf.parse_manifest,
    }
    text_type = guess_content(text)
    if text_type not in dispatch_table:
        return f"Unsupported content type {text_type}"
    f = dispatch_table[text_type]
    return f(text)


def guess_content(text):
    """Guess the content type of the text: mermaid or kubernetes manifest."""
    test = text.strip()
    if test.startswith("graph"):
        return "mermaid"
    if any(("kind" in x for x in yaml.safe_load_all(test))):
        return "kubernetes"
    return None


def d3fend_summary(g: Graph):
    ret = list(
        g.query(
            """
        prefix : <https://par-tec.it/example#>
        prefix d3f: <http://d3fend.mitre.org/ontologies/d3fend.owl#>
        prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT
            ?node ?relation ?artifact ?attack_id ?attack_label
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


def d3fend_summary_html(g: Graph, aggregate=False):
    rows = d3fend_summary(g)
    df = pd.DataFrame(data=rows[1:], columns=rows[0])
    if aggregate:
        df = df.groupby(["node", "artifact", "attack"], as_index=False).agg(",".join)
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
    def _fix_url(url):
        url = str(url).replace("http://d3fend.mitre.org/ontologies/d3fend.owl#", "d3f:")
        url = str(url).replace("https://par-tec.it/example#", ":")
        url = str(url).replace("http://www.w3.org/1999/02/22-rdf-syntax-ns#", "rdf:")
        return url.rsplit("/", 1)[-1]

    node, relation, artifact, attack_id, attack_label = row
    artifact_name = artifact.split("#")[-1]
    artifact_url = f"https://next.d3fend.mitre.org/dao/artifact/d3f:{artifact_name}"

    attack_url = attack_id.replace(".", "/")
    attack_url = f"https://attack.mitre.org/techniques/{attack_url}"
    return (
        _fix_url(node),
        _fix_url(relation),
        f"[{artifact_name}]({artifact_url})",
        f"[{attack_id} - {attack_label}]({attack_url})",
    )
