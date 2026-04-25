from agents.citation_agent import run

def citation_node(state):
    citations = run(state["retrieved_docs"])
    return {"citations": citations}