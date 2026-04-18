from src.memory.memory_store import add_memory, query_memory

def load_memory(user_id: str, query: str):
    return query_memory(user_id, query)


def save_memory(user_id: str, text: str):

    triggers = [
        "tôi thích",
        "remember",
        "i like",
        "my preference"
    ]

    if any(t in text.lower() for t in triggers):
        add_memory(user_id, text)


