import numpy as np
import pytest

from app.services.ingestion.embedding import BgeEmbeddingProvider


@pytest.mark.slow
def test_bge_embedding_dimension_is_768():
    bge = BgeEmbeddingProvider()
    v = bge.embed_one("imperial dress code policy")
    assert isinstance(v, np.ndarray)
    assert v.shape == (768,)


@pytest.mark.slow
def test_bge_similar_texts_more_similar_than_unrelated():
    bge = BgeEmbeddingProvider()
    a = bge.embed_one("dress code policy for off-base events")
    b = bge.embed_one("attire guidelines for personnel travel")
    c = bge.embed_one("reactor coolant shutdown sequence")

    def cos(x, y):
        return float(np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-12))

    assert cos(a, b) > cos(a, c)
