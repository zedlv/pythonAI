import asyncio
import httpx

# 超时时间（秒）
TIME_OUT = 10
# 最大重试次数
MAX_RETRY = 2

URL = "https://postman-echo.com/post"


async def call_llm(prompt: str):
    retries = 0

    while retries < MAX_RETRY:
        try:
            async with httpx.AsyncClient(timeout=TIME_OUT) as client:
                response = await client.post(
                    url=URL,
                    json={"prompt": prompt},
                )
                response.raise_for_status()
                result = response.json()
                # Postman Echo 把 POST 的 JSON 放在 "json" 字段里
                prompt_text = result.get("json", {}).get("prompt")
                return f"LLM模型返回：{prompt_text}"

        except httpx.TimeoutException:
            retries += 1
            if retries >= MAX_RETRY:
                return "LLM调用超时，请稍后再试"

        except httpx.NetworkError:
            retries += 1
            if retries >= MAX_RETRY:
                return "网络异常，模型调用失败"

        except Exception as e:
            retries += 1
            if retries >= MAX_RETRY:
                return f"模型调用失败：{str(e)}"

        await asyncio.sleep(1)
