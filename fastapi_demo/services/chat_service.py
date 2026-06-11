from llm_client import call_llm

# 业务逻辑 + 调用 LLM
async def process_chat_message(msg: str):
    # 调用模型拿到返回
    llm_reply = await call_llm(msg)
    return {
        "status": "ok",
        "your_msg": msg,
        "llm_reply": llm_reply  # 模型返回
    }