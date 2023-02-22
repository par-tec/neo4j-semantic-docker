

## Associate nodes to DigitalArtifacts

```cypher
MATCH p=
  (instance:ns0__Node)-[:rdfs__type*]-> (instance_type) -[:rdfs__subClassOf]-> (artifact:d3f__DigitalArtifact)
RETURN p LIMIT 2000
```

## Principal attacks to a mail infrastructure

1. mermaid -> RDF
2. import RDF in neo4j
3. label  nodes (aka indexing)
4. querying

```cypher

MATCH p=
  (i:ns0__Node)-[:rdfs__subClassOf]->
  (artifact:d3f__DigitalArtifact)
  <-[relation]- (attack:d3f__OffensiveTechnique)
RETURN p LIMIT 2000
```

1. Associate each node with its rdf:type (which is a d3f:DitigalArtifact):

```cypher
(n:ns0__Node)-[:rdf__type]->(artifact:d3f__DigitalArtifact)
```

1. then follow the DigitalArtifact hierarchy to the least-specific type
   with various level of `subClassOf` indirection (0..3)

```cypher
(artifact:d3f__DigitalArtifact)
-[:rdfs__subClassOf*0..3]->  // 0..3 levels of indirection.
(vulnerableArtifact:d3f__DigitalArtifact)
```

1. then find the attack that compromises it

```cypher
(vulnerableArtifact:d3f__DigitalArtifact)
<-[compromises]-(attack:d3f__OffensiveTechnique)
```

The complete query is

```cypher
MATCH p=
 (n:ns0__Node)-[:rdf__type]->
 (artifact:d3f__DigitalArtifact) -[:rdfs__subClassOf*0..3]->
 (vulnerableArtifact:d3f__DigitalArtifact)
  <-[compromises]-(attack:d3f__OffensiveTechnique)
RETURN p
```

1. To identify DigitalArtifacts associated to specific nodes,
   we can replace the `:rdf__type` relation with a generic one

```cypher
MATCH p=
 (n:ns0__Node) -->
 (artifact:d3f__DigitalArtifact) -[:rdfs__subClassOf*0..3]->
 (vulnerableArtifact:d3f__DigitalArtifact)
  <-[compromises]-(attack:d3f__OffensiveTechnique)
RETURN p
```

## Diagram 1

```mermaid
graph TD

Client --> WebMail[WebMail fab:fa-react fa:fa-envelope]
WebMail --> IMAP[IMAP fa:fa-envelope fa:fa-folder]
WebMail --> SMTP[SMTP fa:fa-envelope fa:fa-folder]
IMAP --> Mailstore[(Mailstore fa:fa-envelope fa:fa-folder)]

Client --> IMAP

Authorization[d3f:AuthorizationService] --> |d3f:authenticates| Client
IMAP --o Authorization
SMTP --o Authorization
```

## Diagram 2

```mermaid
graph TD

Client --> WAF[Web Application Firewall fa:fa-shield-alt] --> WebApp --> API[API fa:fa-server]
```

## icons

```mermaid

graph
A["
# OK
fa:fa-lock
fa:fa-lock-open
fa:fa-unlock
fa:fa-key
fa:fa-fingerprint
fa:fa-user-lock
fa:fa-user-unlock
fa:fa-user-clock
fa:fa-alarm-clock
fa:fa-compass
fa:fa-globe
fa:fa-language
fa:fa-eyes
fa:fa-rocket
fa:fa-network-wired svc
fa:fa-cube pod
fa:fa-gear
fa:fa-ban
fa:fa-square
fa:fa-cubes
fa:fa-bug
fa:fa-square-full
fa:fa-hexagon
fa:fa-database
# KO
firewall fa:fa-block-brick
firewall fa:fa-block-brick-fire
backup fa:fa-clock-rotate-left
fa:fa-handcuffs
fa:fa-shield-keyhole
fa:fa-lock-keyhole
fa:fa-unlock-keyhole
fa:fa-lock-hashtag
fa:fa-lock-a
# user
locks: fa:fa-vault
locks: fa:fa-file-lock
locks: fa:fa-binary-lock
locks: fa:fa-nfc-lock
locks: fa:fa-signature-lock
"]

```
