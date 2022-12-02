import logging

from neo4j import GraphDatabase

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def run_queries(neo4j_url: str, queries: list[str]):
    driver = GraphDatabase.driver(neo4j_url, auth=("neo4j", ""))

    ret = []
    with driver.session(database="neo4j") as session:
        for query in queries:
            if not query.strip():
                continue
            try:
                log.debug("Running query: %s", query)
                ret.append(session.run(query))
                log.info("Ran query: %s", query)
            except Exception:
                log.exception(f"Error running query: {query}")

    return ret
