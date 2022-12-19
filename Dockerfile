#
# A semantic graph database for Neo4j.
#
FROM neo4j:4.4.5-community
RUN mkdir /plugins/ -p
RUN wget https://github.com/neo4j-labs/neosemantics/releases/download/4.4.0.3/neosemantics-4.4.0.3.jar -O /plugins/neosemantics.jar
RUN chown -R 1001 /plugins /logs /data && chmod g+rwX  /plugins /logs /data
USER 1001
