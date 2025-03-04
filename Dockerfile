#
# A semantic graph database for Neo4j.
#
FROM neo4j:5.20.0-community
RUN mkdir /plugins/ -p
RUN wget https://github.com/neo4j-labs/neosemantics/releases/download/5.20.0/neosemantics-5.20.0.jar -O /plugins/neosemantics.jar
RUN chown -R 1000:1000 /plugins /logs /data && \
    chmod g+rwX  /plugins /logs /data
USER 1000:1000
