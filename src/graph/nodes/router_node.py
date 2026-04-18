def router(state):
    q = state["question"].lower()

    if "tóm tắt" in q:
        return "summarize"
    elif "ôn tập" in q:
        return "study"
    else:
        return "qa"