from src.rag.retriever import rag_answer

def main():
    while True:
        query = input("\nQuestion: ")
        if query.lower() in ["exit", "quit"]:
            break

        result = rag_answer(
            query=query,
            retrieval_mode="dense",
            use_rerank=False,
            verbose=True
        )

        print("\n=== ANSWER ===")
        print(result["answer"])

        print("\n=== SOURCES ===")
        print(result["sources"])

if __name__ == "__main__":
    main()