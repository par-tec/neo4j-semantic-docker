import logging
import re
import unicodedata
from time import time

import yaml
from rdflib import Graph
from rdflib.namespace import RDF

import kuberdf
import mermaidrdf

log = logging.getLogger(__name__)
HEADERS = ["node", "relation", "artifact", "technique"]


def filter_mermaid(text, mermaid_filter, skip_filter=None):
    # Assumes that subgraphs are not nested
    # and that they are at the end of the text.
    log.warning(f"Filtering mermaid text with {mermaid_filter}")
    re_mermaid_filter = re.compile(f"""^.*({mermaid_filter}).*""", re.I)
    ret = []
    subgraphs = re.findall(r"(\nsubgraph.*?\nend)", text, re.DOTALL)
    matching_subgraphs = []
    for subgraph in subgraphs:
        if re.match(".*" + mermaid_filter + ".*", subgraph, re.DOTALL):
            subgraph_name = re.search(r"subgraph\s+([^[]+)\s*", subgraph).group(1)
            matching_subgraphs.append(subgraph_name)
    nodes = set()
    for line in text.splitlines():
        if skip_filter and re.match(".*" + skip_filter + ".*", line):
            log.debug("Skipping line: " + line)
            continue

        s_p_o = mermaidrdf.RE_LINE.match(line)
        s_p_o = s_p_o.groups() if s_p_o else [None] * 9
        s, o = s_p_o[0], s_p_o[8]
        items = {s, o}
        log.debug(f"Extracting resources from line: (s={s}, o={o}")

        if s in ("subgraph", "graph", "classDef", "class", "click"):
            ret.append(line)
            continue

        # Don't render empty subgraphs.
        if s == "end":
            if ret[-1].startswith("subgraph "):
                ret.pop()
            else:
                ret.append(line)
            continue

        is_required = re_mermaid_filter.match(line)
        is_inferred = items & nodes
        if is_required or is_inferred:
            log.debug(
                f"Found matching line: {line} (is_required={is_required}, is_inferred={is_inferred})"
            )
            ret.append(line)
            if s:
                nodes.add(s)
            if o:
                nodes.add(o)
            continue
        # If a subgraph contains the filter, include any line that contains the subgraph name.
        if any((x for x in matching_subgraphs if "_" in x and x in line)):
            log.debug("Found matching subgraph: " + line)
            ret.append(line)
            continue

        log.debug(f"Filtering out {line}")

    text_mmd = "\n".join(ret)
    log.info(f"Filtered mermaid text:\n{text_mmd}")
    return text_mmd


def rdf_to_mermaid_filtered(g, match=""):
    x = Graph()
    # Add all g triples to x
    for s, p, o in g:
        if (p, o) == (RDF.type, kuberdf.NS_K8S.Namespace):
            x.add((s, p, o))
        if match in f"{s}{o}":
            x.add((s, p, o))
    return rdf_to_mermaid(x)


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
    mermaid = "graph LR\n" + "\n".join(
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
    try:
        import pandas as pd

        rows = summary_function(g)
        df = pd.DataFrame(data=rows[1:], columns=rows[0])
        if aggregate:
            df = df.groupby(["node", "artifact", "technique"], as_index=False).agg(
                ",".join
            )
        df = df[HEADERS]
        html = df.to_html(
            formatters=[markdown_link_to_html_link] * len(HEADERS), escape=False
        )
    except Exception as e:
        log.exception(e)
        html = "<pre>" + str(e) + "</pre>"
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


def render_unicode_emojis(text):
    re_emoji = re.compile("u:u-([a-zA-Z0-9_-]+)")
    return re_emoji.sub(
        lambda match: unicodedata.lookup(
            match.group(1).upper().replace("_", " ").replace("-", " ")
        ),
        text,
    )
