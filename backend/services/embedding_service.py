import asyncio
from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self,logger):
        self.logger = logger
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.dim = self.model.get_sentence_embedding_dimension()
        self.logger.info(f"[EmbeddingService] 初始化模型: {self.model}, embedding_dim={self.dim}")

    async def embed(self, text: str) -> list[float]:
        """
        异步生成 embedding
        """
        await asyncio.sleep(0)  # 保持 async 接口
        vector = self.model.encode(text).tolist()
        return vector

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts)
        return vectors.tolist()