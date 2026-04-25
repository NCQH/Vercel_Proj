from fastapi import APIRouter
from graph.builder import graph

router = APIRouter()

@router.post("/ask")
def ask(question: str):
    result = graph.invoke({"question": question})
    return result