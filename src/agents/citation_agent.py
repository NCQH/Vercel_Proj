def run(docs):
    citations = []

    for d in docs:
        meta = d.metadata
        citations.append(f"{meta.get('source')} - page {meta.get('page')}")

    return list(set(citations))