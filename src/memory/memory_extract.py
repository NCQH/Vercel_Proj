def extract_memory(text: str):
    """
    Extract stable user facts
    """

    memories = []

    text_l = text.lower()

    if "tôi thích" in text_l:
        memories.append(text)

    if "tôi không thích" in text_l:
        memories.append(text)

    if "tôi là" in text_l:
        memories.append(text)

    if "tên tôi" in text_l:
        memories.append(text)

    if "hãy nhớ" in text_l or "nhớ rằng" in text_l:
        memories.append(text)

    if "i prefer" in text_l:
        memories.append(text)

    if "i am" in text_l:
        memories.append(text)

    if "my name is" in text_l:
        memories.append(text)

    if "i don't like" in text_l:
        memories.append(text)

    if "remember" in text_l:
        memories.append(text)

    return memories