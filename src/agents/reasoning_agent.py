from langchain.chat_models import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")

def run(question, docs):
    context = "\n".join([d.page_content for d in docs])

    prompt = f"""
Bạn là trợ giảng AI. Trả lời dựa trên context:

{context}

Question: {question}
"""

    return llm.invoke(prompt).content