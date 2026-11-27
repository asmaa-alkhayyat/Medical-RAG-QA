from FlagEmbedding import BGEM3FlagModel

model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False)


def embed_texts(texts):
    result = model.encode(texts, batch_size=12, max_length=8192)
    vectors = result["dense_vecs"]
    return vectors.tolist()