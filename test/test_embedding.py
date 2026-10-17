import httpx

from app.config import get_settings

settings = get_settings()

URL = f"{settings.dashscope_base_url.rstrip('/')}/embeddings"   # ← 补上 /embeddings
API_KEY = settings.dashscope_api_key
MODEL = settings.embed_model_name




def test1():
    resp = httpx.post(
        URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "input": "今天一起看了日落，杭州西湖",
        },
        timeout=30,
    )

    print("HTTP 状态:", resp.status_code)

    if resp.status_code != 200:
        print("请求失败，返回内容：")
        print(resp.text)
        return

    data = resp.json()
    embedding = data["data"][0]["embedding"]

    print("模型:", data.get("model"))
    print("向量维度:", len(embedding))
    print("前 5 个值:", embedding[:5])
    print("usage:", data.get("usage"))


def test2():
    from app.services.embedding_client import get_embedding
    emb=get_embedding()
    vec=emb.encode("今天一起看了日落")
    print("维度:", len(vec))
    print("前 5 个值:", vec[:5])

if __name__ == "__main__":
    test2()