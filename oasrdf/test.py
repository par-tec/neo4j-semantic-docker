import logging

from rdflib import Graph, URIRef

from . import parse, parse_all, parse_paths, parse_securitySchemes, parse_servers

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def test_parse_paths():
    api = parse("openapi.yaml")
    g = Graph()
    map(g.add, parse_paths(api))
    [g.add(x) for x in parse_paths(api)]
    assert len(g) == 6
    log.info(g.serialize(format="turtle"))


def test_parse_all():
    api = parse("openapi.yaml")
    g = Graph()
    parse_all(g, api)

    assert (
        URIRef("https://localhost#getOauthEndpoint"),
        URIRef("https://example.com/oauth/token"),
    ) in list(
        g.query(
            """
    prefix ns1: <https://d3fend.org/ontology#>
    SELECT DISTINCT * WHERE {
            ?a ns1:accesses+ ?b
            . ?b a ns1:AuthorizationService
            . ?a a ns1:WebResourceAccess}
    """
        )
    )
    assert len(g) == 14
    log.info(g.serialize(format="turtle"))


def test_parse_servers():
    api = parse("openapi.yaml")
    g = Graph()
    parse_servers(g, api)
    assert len(g) == 2
    log.info(g.serialize(format="turtle"))


def test_parse_securitySchemes():
    api = parse("openapi.yaml")
    g = Graph()
    parse_securitySchemes(g, api)
    assert len(g) == 10
    log.info(g.serialize(format="turtle"))
