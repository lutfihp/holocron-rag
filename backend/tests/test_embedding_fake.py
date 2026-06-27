import numpy as np

from app.services.ingestion.embedding import FakeEmbeddingProvider


def test_same_text_same_vector():
    fake = FakeEmbeddingProvider()
    v1 = fake.embed_one("the dress code applies to all imperial personnel")
    v2 = fake.embed_one("the dress code applies to all imperial personnel")
    assert np.allclose(v1, v2)


def test_vector_dimension_is_768():
    fake = FakeEmbeddingProvider()
    v = fake.embed_one("anything")
    assert v.shape == (768,)


def test_similar_texts_have_higher_cosine_than_unrelated():
    fake = FakeEmbeddingProvider()
    a = fake.embed_one("dress code policy for off-base events")
    b = fake.embed_one("dress code rules for off-base activities")
    c = fake.embed_one("reactor coolant shutdown sequence procedures")

    def cos(x, y):
        return float(np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-12))

    assert cos(a, b) > cos(a, c)


def test_embed_batch_returns_one_vector_per_input():
    fake = FakeEmbeddingProvider()
    vecs = fake.embed_batch(["one", "two", "three"])
    assert len(vecs) == 3
    assert all(v.shape == (768,) for v in vecs)
