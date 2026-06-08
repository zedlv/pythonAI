def process_chat_message(msg: str):
    return {
        "status": "ok",
        "your_msg": msg,
        "reply": f"你说的是：{msg}"
    }