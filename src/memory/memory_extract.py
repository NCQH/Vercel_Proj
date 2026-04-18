def extract_memory(text: str):
    """
    Extract stable user facts
    """

    memories = []

    text_l = text.lower()

    if "tôi thích" in text_l:
        memories.append(text)

    if "i prefer" in text_l:
        memories.append(text)

    if "remember" in text_l:
        memories.append(text)

    return memories