import logging
from pathlib import Path
from time import time

import pandas as pd
import yaml
from rdflib import Graph
from rdflib.term import Literal, URIRef

import kuberdf
import mermaidrdf

log = logging.getLogger(__name__)

turtle_text = """
@prefix : <https://par-tec.it/example#> .
@prefix d3f: <http://d3fend.mitre.org/ontologies/d3fend.owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

:Client a :Node ;
    d3f:accesses :WebMail ;
    d3f:uses d3f:LoginSession .

:IMAP a d3f:FileSystem,
        d3f:MailService,
        :Node ;
    rdfs:label "IMAP fa:fa-envelope fa:fa-folder" ;
    d3f:accesses :Mailstore ;
    d3f:reads :Authorization ;
    d3f:related d3f:Email .

:Mailstore a d3f:FileSystem,
        :Node ;
    rdfs:label "Mailstore fa:fa-envelope fa:fa-folder" ;
    d3f:related d3f:Email .

:SMTP a d3f:FileSystem,
        d3f:MailService,
        d3f:MessageTransferAgent,
        :Node ;
    rdfs:label "SMTP fa:fa-envelope fa:fa-folder" ;
    d3f:reads :Authorization ;
    d3f:related d3f:Email .

:WebMail a d3f:GraphicalUserInterface,
        d3f:WebServerApplication,
        :Node ;
    rdfs:label "WebMail fab:fa-react fa:fa-envelope" ;
    d3f:accesses :IMAP,
        :SMTP ;
    d3f:related d3f:Email .

:Authorization a :Node ;
    rdfs:label "d3f:AuthorizationService fa:fa-user-secret" ;
    d3f:authenticates :Client ;
    d3f:produces d3f:AuthenticationLog,
        d3f:LoginSession ;
    d3f:related d3f:UserAccount .

"""


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


def test_as_graph():
    g = Graph()
    g.parse(data=turtle_text, format="turtle")
    g.parse("../d3fend.ttl", format="turtle")
    html = d3fend_summary(g)
    Path("/tmp/foo.html").write_text(html)
    raise NotImplementedError


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

    headers = ["node", "relation", "artifact", "attack"]
    return [headers] + [render_row(row) for row in ret]


def test_d3fend_summary_pd():
    g = initialize_graph(["../d3fend.ttl"])
    g.parse(data=turtle_text, format="turtle")
    rows = d3fend_summary(g)
    df = pd.DataFrame(rows[1:], columns=rows[0])
    raise NotImplementedError


def d3fend_summary_html(g: Graph):
    summary = d3fend_summary(g)
    html = list_as_html_table(summary)
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
        return f'<a href="{url[:-1]}">{label}</a>'
    return markdown_link


def test_render_row():
    testcases = [
        (
            URIRef("https://par-tec.it/example#Authorization"),
            URIRef("http://d3fend.mitre.org/ontologies/d3fend.owl#related"),
            URIRef("http://d3fend.mitre.org/ontologies/d3fend.owl#UserAccount"),
            Literal("T1136"),
            Literal("Create Account"),
        )
    ]
    for row in testcases:
        render_row(row)
        raise NotImplementedError


def render_row(row):
    def _fix_url(url):
        url = str(url).replace("http://d3fend.mitre.org/ontologies/d3fend.owl#", "d3f:")
        url = str(url).replace("https://par-tec.it/example#", ":")
        return url.rsplit("/", 1)[-1]

    node, relation, artifact, attack_id, attack_label = row
    artifact_name = artifact.split("#")[-1]
    artifact_url = f"https://next.d3fend.mitre.org/dao/artifact/d3f:{artifact_name}"
    d3f_attack_url = (
        f"https://next.d3fend.mitre.org/offensive-technique/attack/{attack_id}"
    )
    attack_url = f"https://attack.mitre.org/techniques/{attack_id}"
    return (
        _fix_url(node),
        _fix_url(relation),
        f"[{artifact_name}]({artifact_url})",
        f"[{attack_id} - {attack_label}]({attack_url})",
    )
