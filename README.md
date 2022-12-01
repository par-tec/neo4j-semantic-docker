# Neo4j + D3FEND

In this repo you can find an ongoing experiment of using D3FEND for design analysis on
kubernetes / openshift deployment files.

This is not for production :)

The steps are the following:

1. transform the Kubernetes manifests into RDF;
2. load the RDF into the Neo4j instance you find in docker-compose.

## Running

This repo creates an RDF representation of a Kube deployment.

```
tox -e kube-to-rdf -- ${MANIFEST_DIR} ${DEST_FILE}
ls -la ${DEST_FILE}.ttl
```

Now import the RDF into Neo4j.

```bash
docker-compose up -d neo4j
```

Access the neo4j container and run  via the CLI

```bash
docker-compose exec neo4j bash
$ cd /code
$ cypher-shell -u neo4j  -f /code/neo4j.init --fail-at-end <<< ""
```

Query the graph

```cypher
MATCH
        (n) -- (p:ns0__Kind)  // all nodes connected with a k8s resource
WHERE
        NOT n:ns0__Namespace
RETURN n
```

Show entities

```cypher
match (p) -- (n:ns0__Kind)
where
        p.rdfs__label is null
        or not p.rdfs__label = "ndc-dev"
return p
```

Show access patterns

```cypher
match (n:ns0__Kind) -- (p) <-[:ns0__accesses*]- (q)
where not p:ns0__Namespace
return q
```

## pre-commit

Pre-commit checks your files before committing. It can lint, format or do
other checks on them.

Once you install it via

        pip3 install pre-commit --user

You can run it directly via

        pre-commit run --all-files


Or install it as a pre-commit hook

        pre-commit install

## .github/workflows
