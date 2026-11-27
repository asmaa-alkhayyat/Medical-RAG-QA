from FlagEmbedding import BGEM3FlagModel

model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False)


def embed_texts(texts):
    result = model.encode(texts, batch_size=12, max_length=8192)
    vectors = result["dense_vecs"]
    return vectors.tolist()


if __name__ == "__main__":
    sentences = [
        "What is the treatment of severe hypoglycaemia?",
        "ما علاج انخفاض السكر الشديد؟",
        "The weather is sunny today",
    ]

    vectors = embed_texts(sentences)
    print("Number of vectors:", len(vectors))
    print("Length of first vector:", len(vectors[0]))

    # similarity between each pair of sentences
    for i in range(len(sentences)):
        for j in range(i + 1, len(sentences)):
            similarity = 0
            for k in range(len(vectors[i])):
                similarity = similarity + vectors[i][k] * vectors[j][k]
            print("Sentence", i + 1, "and sentence", j + 1, ":", round(similarity, 3))