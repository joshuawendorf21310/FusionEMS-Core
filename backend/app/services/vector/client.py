class VectorClient:
    def index(self, doc_id: str, vector: list):
        return {"indexed": doc_id}