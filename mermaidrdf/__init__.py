import logging
import re

from rdflib import Graph, Namespace

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

NS_DEFAULT = Namespace("https://par-tec.it/example#")
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
    (
        "docker",
        "kubernetes",
    ): ("d3f:ContainerOrchestrationSoftware",),
    ("fab:fa-docker",): ("d3f:ContainerProcess",),
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
FONTAWESOME_MAP = {
    ("fa-envelope",): ("d3f:Email",),
    ("fa-user-secret",): ("d3f:UserAccount",),
    ("fa-globe",): ("d3f:InternetNetworkTraffic",),
    ("fa-docker",): ("d3f:ContainerOrchestrationSoftware",),
    ("fa-clock",): ("d3f:TaskSchedule",),
}
D3F_PROPERTIES = {
    "abuses",
    "accessed-by",
    "broader",
    "broader-transitive",
    "cited-by",
    "claimed-by",
    "contained-by",
    "created-by",
    "deceives",
    "depends-on",
    "employed-by",
    "evaluated-by",
    "evaluator",
    "exactly",
    "expected-latency",
    "impairs",
    "inventoried-by",
    "invoked-by",
    "loaded-by",
    "mapped-by",
    "may-be-deceived-by",
    "may-be-detected-by",
    "may-be-evicted-by",
    "may-be-hardened-against-by",
    "may-be-isolated-by",
    "modified-by",
    "modifies-part",
    "narrower",
    "narrower-transitive",
    "process-parent",
    "produced-by",
    "producer",
    "publisher",
    "recorded-in",
    "related",
    "seller",
    "submitter",
    "used-by",
    "validator",
    "writes",
    "addressed-by",
    "attached-to",
    "authorizes",
    "configures",
    "connects",
    "creator",
    "deceives-with",
    "dependent",
    "extends",
    "has-account",
    "has-dependent",
    "has-feature",
    "has-implementation",
    "has-location",
    "has-recipient",
    "has-sender",
    "hides",
    "installs",
    "kb-reference",
    "license",
    "limits",
    "may-be-contained-by",
    "may-be-created-by",
    "may-be-invoked-by",
    "may-be-modified-by",
    "may-deceive",
    "may-detect",
    "may-disable",
    "may-execute",
    "may-harden",
    "may-isolate",
    "neutralizes",
    "owns",
    "process-ancestor",
    "process-image-path",
    "process-user",
    "provider",
    "provides",
    "publishes",
    "summarizes",
    "terminates",
    "unmounts",
    "updates",
    "use-limits",
    "assessed-by",
    "deletes",
    "detects",
    "drives",
    "enabled-by",
    "features",
    "forges",
    "implemented-by",
    "implements",
    "injects",
    "interprets",
    "kb-reference-of",
    "may-be-accessed-by",
    "may-be-tactically-associated-with",
    "may-counter",
    "may-interpret",
    "may-map",
    "may-run",
    "obfuscates",
    "originates-from",
    "queries",
    "sells",
    "strengthens",
    "validates",
    "author",
    "cites",
    "copies",
    "encrypts",
    "has-evidence",
    "manages",
    "may-evict",
    "may-query",
    "process-property",
    "records",
    "addresses",
    "assesses",
    "claims",
    "d3fend-kb-object-property",
    "disables",
    "evicts",
    "has-member",
    "isolates",
    "latency",
    "member-of",
    "attack-may-be-countered-by",
    "d3fend-tactical-verb-property",
    "evaluates",
    "may-counter-attack",
    "may-transfer",
    "verifies",
    "counters",
    "runs",
    "loads",
    "may-add",
    "reads",
    "blocks",
    "filters",
    "semantic-relation",
    "spoofs",
    "hardens",
    "inventories",
    "uses",
    "authenticates",
    "may-produce",
    "adds",
    "executes",
    "monitors",
    "restricts",
    "maps",
    "may-create",
    "may-be-associated-with",
    "invokes",
    "may-access",
    "d3fend-catalog-object-property",
    "may-contain",
    "may-invoke",
    "creates",
    "enables",
    "contains",
    "analyzes",
    "accesses",
    "may-modify",
    "associated-with",
    "produces",
    "modifies",
}


def mermaid_to_rdf(mermaid):
    mermaid = mermaid.strip()
    # Ensure that the mermaid text starts with "graph "
    if not mermaid.startswith(("graph ", "graph")):
        raise ValueError("The mermaid text must start with 'graph'")
    # Split the mermaid text into lines, skipping the first line.
    lines = mermaid.splitlines()[1:]

    for line in lines:
        for sentence in parse_line(line):
            yield sentence


def parse_mermaid(mermaid: str):
    g = Graph()
    g.bind("", NS_DEFAULT)
    g.bind("d3f", "http://d3fend.mitre.org/ontologies/d3fend.owl#")
    g.bind("rdfs", "http://www.w3.org/2000/01/rdf-schema#")
    turtle = """@prefix : <https://par-tec.it/example#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix d3f: <http://d3fend.mitre.org/ontologies/d3fend.owl#> .
    """ + "\n".join(
        mermaid_to_rdf(mermaid)
    )
    g.parse(data=turtle, format="turtle")
    return g.serialize(format="turtle")


def render_node(id_, label, sep):
    type_ = ":Node"
    rdf = [f":{id_} a {type_} ."]

    if sep == "[(":
        type_ = "d3f:DatabaseServer"
    elif sep == "[[":  # FIXME: is this ok?
        type_ = "d3f:Server"
    rdf.append(f":{id_} a {type_} .")
    if label:
        rdf += [f':{id_} rdfs:label """{label}""" .']

    label = label or id_
    for softwares, d3f_classes in SW_MAP.items():
        if any((x in label.lower() for x in softwares)):
            rdf += [f":{id_} a {','.join(d3f_classes)} ."]
    for needles, d3f_classes in FONTAWESOME_MAP.items():
        if any((x in label.lower() for x in needles)):
            log.info("Found %s in %s", needles, label)
            rdf += [f":{id_} d3f:related {','.join(d3f_classes)} ."]

    return id_, rdf


def parse_line2(line):
    """Parse a mermaid line in the possible forms:
    1. x[label]
    2. x[label]-->y
    3. x[label]-->|comment| y
    4. x --> y --> z
    """
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

            yield from _parse_relation(node_id0, node_id, predicate, relation0)

        node_id0, arrow0, relation0 = node_id, arrow, relation


def _parse_relation(src, dst, predicate, relation):
    """Parse a relation between two nodes."""
    if not relation:
        yield f":{src} {predicate} :{dst} ."
        return
    if relation.startswith("d3f:") and relation[4:] in D3F_PROPERTIES:
        yield f":{src} {relation} :{dst} ."

        if relation == "d3f:authenticates":
            yield f":{src} d3f:produces d3f:LoginSession ."
            yield f":{dst} d3f:uses d3f:LoginSession ."
            yield f":{src} d3f:produces d3f:AuthenticationLog ."
        return

    # Explicit the relationship.
    yield f":{src} {predicate} :{dst} ."

    # Introduces a relation based on a specific d3f:DigitalArtifact,
    # e.g. :App --> |via d3f:DatabaseQuery| :Database
    for needle in re.findall(r"(d3f:[A-Za-z0-9._\.-]+)", relation):
        # TODO verify that the relation is a valid d3f:DigitalArtifact.
        yield f":{src} d3f:produces {needle} ."
        yield f":{dst} d3f:uses {needle} ."
        return

    # Introduces a relation based on a specific d3f:DigitalArtifact,
    # e.g. :Client --> |via fa:fa-envelope| :MTA
    for rel in re.findall(r"(?:fab?:(fa-[a-z0-9-]+))", relation):
        for needles, d3f_classes in FONTAWESOME_MAP.items():
            if rel not in needles:
                continue
            for d3f_class in d3f_classes:
                yield f":{src} d3f:produces {d3f_class} ."
                yield f":{dst} d3f:uses {d3f_class} ."
        return


def extract_mermaid(text: str):
    re_mermaid = re.compile("```mermaid\n.*?\n```", re.DOTALL | re.MULTILINE)
    return [graph[10:-3].strip() for graph in re_mermaid.findall(text)]
