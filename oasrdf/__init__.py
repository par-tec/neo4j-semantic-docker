import logging

from rdflib import RDF, RDFS, Literal, Namespace, URIRef

D3F = Namespace("https://d3fend.org/ontology#")
LOCAL = Namespace("https://localhost#")
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def parse_servers(api):
    for server in api.servers:
        server_uri = URIRef(server.url)
        yield ((server_uri, RDF.type, D3F.WebServer))
        if server.description:
            yield ((server_uri, RDFS.comment, Literal(server.description)))


def parse_securitySchemes(api):
    for name, scheme in api.security_schemas.items():
        scheme_uri = LOCAL[f"securitySchemes/{name}"]
        yield ((scheme_uri, RDF.type, D3F.WebAuthentication))
        if scheme.description:
            yield ((scheme_uri, RDFS.comment, Literal(scheme.description)))
        try:
            if scheme.scheme.name == "bearer":
                yield ((scheme_uri, RDF.type, D3F.AccessToken))
        except (AttributeError,):
            pass

        if scheme.type.name.lower() == "oauth2":
            for flow_id, flow in scheme.flows.items():
                flow_uri = scheme_uri + "/" + flow_id.name
                yield ((flow_uri, RDF.type, D3F.Authorization))
                yield ((scheme_uri, D3F.accesses, flow_uri))
                if flow.authorization_url:
                    yield ((flow_uri, D3F.accesses, URIRef(flow.authorization_url)))
                    yield (
                        (
                            URIRef(flow.authorization_url),
                            RDF.type,
                            D3F.AuthorizationService,
                        )
                    )
                if flow.token_url:
                    yield ((flow_uri, D3F.accesses, URIRef(flow.token_url)))
                    yield ((URIRef(flow.token_url), RDF.type, D3F.AuthorizationService))
                if flow.refresh_url:
                    yield ((flow_uri, D3F.accesses, URIRef(flow.refresh_url)))
                    yield (
                        (URIRef(flow.refresh_url), RDF.type, D3F.AuthorizationService)
                    )

                for scope in flow.scopes:
                    yield (
                        (flow_uri, D3F.implements, D3F.CredentialTransmissionScoping)
                    )


def parse_paths(api):
    for path in api.paths:
        path.url
        for operation in path.operations:
            operation_uri = LOCAL[operation.operation_id]
            yield ((operation_uri, RDF.type, D3F.WebResourceAccess))
            for server in api.servers:
                yield ((operation_uri, RDFS.member, URIRef(server.url)))

            for securityScheme in operation.security:
                for securitySchemeName, securitySchemeScopes in securityScheme.items():
                    yield (
                        (
                            operation_uri,
                            D3F.accesses,
                            LOCAL[f"securitySchemes/{securitySchemeName}"],
                        )
                    )


def parse_all(api):
    for f in parse_servers, parse_securitySchemes, parse_paths:
        yield from f(api)
