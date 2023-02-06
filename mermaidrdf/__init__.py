import logging
import re

import rdflib

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

MERMAID_KEYWORDS = (
    "subgraph",
    "end",
    "classDef",
    "class",
)
PAT_LABEL = r"(.*?)"
PAT_OPEN = r"|".join((r"\[\[", r"\[\(", r"\(\(", r"\{\{", r"\[\/"))
PAT_CLOSE = r"|".join((r"\]\]", r"\)\]", r"\)\)", r"\}\}", r"\/\]"))
PAT_NODE = r"(\w+)" r"(([\(\[\{\/]{1,2})" + PAT_LABEL + r"([\)\]\}\/]{1,2}))?"
PAT_ARROW = r"\s*(-->|--o|-[.-]+-[>ox]?)" + r"\s*" + r"(?:\|(.*)?\|)?\s*"
PAT_LINE = rf"{PAT_NODE}({PAT_ARROW}{PAT_NODE})*"
RE_ARROW = re.compile(PAT_ARROW)
RE_LINE = re.compile(PAT_LINE)
RE_NODE = re.compile(PAT_NODE)
# a python regular expression matching an unicode character or a number


def mermaid_to_rdf(mermaid):
    mermaid = mermaid.strip()
    # Ensure that the mermaid text starts with "graph "
    if not mermaid.startswith("graph "):
        raise ValueError("The mermaid text must start with 'graph '")
    # Remove the "graph " from the mermaid text
    mermaid = mermaid[6:]
    # Split the mermaid text into lines
    lines = mermaid.splitlines()

    for line in lines:
        for sentence in parse_line(line):
            yield sentence


def parse_mermaid(mermaid: str):
    g = rdflib.Graph()
    turtle = "\n".join(mermaid_to_rdf(mermaid))

    turtle = (
        """
    @prefix : <https://par-tec.it/example#> .
    @prefix d3f:  <http://d3fend.mitre.org/ontologies/d3fend.owl#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    """
        + turtle
    )
    g.parse(data=turtle, format="turtle")
    return g.serialize(format="turtle")


def render_node(id_, label, sep):
    type_ = ":Node"

    if sep == "[(":
        type_ = "d3f:DatabaseServer"
    elif sep == "[[":
        type_ = "d3f:Server"
    rdf = [f":{id_} a {type_} ."]

    SW_MAP = {
        (
            "nginx",
            "apache",
            "httpd",
        ): ("d3f:WebServer",),
        (
            "mysql",
            "mariadb",
            "postgresql",
            "mongodb",
        ): ("d3f:DatabaseServer",),
        (
            "rabbitmq",
            "kafka",
            "pulsar",
        ): ("d3f:DatabaseServer", "d3f:Server"),
        (
            "elasticsearch",
            "solr",
        ): ("d3f:DatabaseServer",),
        (
            "postfix",
            "smtp",
        ): ("d3f:MailService", "d3f:MessageTransferAgent"),
        ("dns", "bind"): ("d3f:DNSServer",),
        ("auth0", "okta", "keycloak", "oauth"): (
            "d3f:AuthorizationServer",
            "d3f:AuthenticationService",
        ),
        ("avas", "clamav", "antispam"): (
            "d3f:ApplicationLayerFirewall",
            "d3f:MailService",
        ),
        (
            "imap",
            "lmtp",
            "dovecot",
        ): ("d3f:MailService",),
        (
            "gitlab",
            "github",
            "bitbucket",
            "fab:fa-github",
            "fab:fa-gitlab",
            "fab:fa-git",
        ): ("d3f:VersionControlSystem",),
        (
            "jenkins",
            "gitlab-ci",
            "github",
        ): ("d3f:SoftwareDeploymentTool",),
        ("docker", "kubernetes", "fab:fa-docker"): (
            "d3f:ContainerOrchestrationSoftware",
        ),
        ("fa-server",): ("d3f:Server",),
        ("fab:fa-python", "fab:fa-php"): ("d3f:ExecutableScript",),
        ("fa-folder",): ("d3f:FileSystem",),
        ("fa-desktop",): ("d3f:WebServerApplication", "d3f:GraphicalUserInterface"),
        ("fab:fa-linux", "fab:fa-ubuntu", "fab:fa-redhat"): ("d3f:OperatingSystem",),
        ("fab:fa-angular", "fab:fa-react", "fab:fa-vuejs"): (
            "d3f:WebServerApplication",
            "d3f:GraphicalUserInterface",
        ),
    }
    USE_MAP = {
        ("fa-envelope",): ("d3f:Email",),
    }
    if label:
        rdf += [f':{id_} rdfs:label """{label}""" .']

    label = label or id_
    for softwares, d3f_classes in SW_MAP.items():
        if any((x in label.lower() for x in softwares)):
            rdf += [f":{id_} a {','.join(d3f_classes)} ."]
    for needles, d3f_classes in USE_MAP.items():
        if any((x in label.lower() for x in needles)):
            rdf += [f":{id_} d3f:accesses {','.join(d3f_classes)} ."]

    return id_, rdf


def parse_line2(line):
    # Split a mermaid line into nodes by the arrow, grouping the nodes and the arrow
    # together in a tuple
    # Example: A --> B --> C
    # will be split into [(A, -->), (B, -->), (C, )]
    # The last tuple will have an empty arrow
    ret = RE_ARROW.split(line)
    # Pad the list with None to make sure we have a multiple of 3 length.
    ret = ret + [None] * (3 - len(ret) % 3)
    return [tuple(ret[i : i + 3]) for i in range(0, len(ret), 3)]


def parse_line(line):
    """Parse a mermaid line consisting of two nodes and an arrow.
    If the line is not valid, skip it."""
    # Skip empty lines
    line = line.strip()
    if not line or len(line) < 5 or line.startswith("%%"):
        return

    if line.startswith(MERMAID_KEYWORDS):
        log.warning(f"Unsupported KEYWORD: {line}")
        return
    # if the line doesn't match x-->y, skip it
    if not RE_LINE.match(line):
        log.warning(f"Unsupported RE_LINE: {line}")
        return
    # Split the line into the two nodes and the arrow
    # according to the mermaid syntax. The resulting line will be
    # something like 5-1-5
    parsed_line = parse_line2(line)
    log.info(f"Parsed line: {line} to: {parsed_line}")

    node_id0, arrow0, relation0 = None, None, None
    for node, arrow, relation in parsed_line:
        id_, _, sep, label, _ = RE_NODE.match(node).groups()
        # Remove the trailing and leading quotes from the nodes
        node_id, node1_rdf = render_node(id_=id_, label=label, sep=sep)
        yield from node1_rdf
        if node_id0:
            # TODO handle the relation.

            if not (node and arrow0):
                raise NotImplementedError
            # Create the RDF
            if arrow0.endswith("->"):
                predicate = "d3f:accesses"
            elif arrow0.endswith("-o"):
                predicate = "d3f:reads"
            elif arrow0.endswith("-"):
                predicate = ":connected"
            else:
                raise NotImplementedError(f"Unsupporte predicate: {arrow}")
            if relation0 and relation0.startswith("d3f:"):
                predicate = relation0
            yield f":{node_id0} {predicate} :{node_id} ."
        node_id0, arrow0, relation0 = node_id, arrow, relation


def extract_mermaid(text: str):
    re_mermaid = re.compile("```mermaid\n.*?\n```", re.DOTALL | re.MULTILINE)
    return [graph[10:-3].strip() for graph in re_mermaid.findall(text)]
