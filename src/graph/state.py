from typing import TypedDict, List

class GraphState(TypedDict):
    question: str
    retrieved_docs: List
    answer: str
    citations: List[str]