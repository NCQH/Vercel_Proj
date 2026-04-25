from agents.retrieval_agent import run

def retrieval_node(state):
    docs = run(state["question"])
    return {"retrieved_docs": docs}