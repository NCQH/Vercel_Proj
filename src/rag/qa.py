from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.rag.retriever import get_retriever


def build_qa():
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0
    )

    retriever = get_retriever()

    prompt = ChatPromptTemplate.from_template("""
Answer the question based only on the context below.

Context:
{context}

Question:
{question}
""")

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # 🔥 LCEL pipeline
    qa_chain = (
        {
            "context": retriever | format_docs,
            "question": lambda x: x
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return qa_chain