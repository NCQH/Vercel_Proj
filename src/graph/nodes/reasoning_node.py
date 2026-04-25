from agents.reasoning_agent import run

def reasoning_node(state):
    answer = run(state["question"], state["retrieved_docs"])
    return {"answer": answer}