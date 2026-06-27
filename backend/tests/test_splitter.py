from app.services.ingestion.splitter import split_text


def test_short_text_one_chunk():
    chunks = split_text("This is a single short sentence.", chunk_size=512, overlap=50)
    assert chunks == ["This is a single short sentence."]


def test_long_text_multiple_chunks():
    sentences = [f"This is sentence number {i}." for i in range(30)]
    text = " ".join(sentences)
    chunks = split_text(text, chunk_size=50, overlap=10)
    assert len(chunks) > 1


def test_chunks_preserve_sentence_boundaries():
    sentences = [f"Sentence {i} content here." for i in range(10)]
    text = " ".join(sentences)
    chunks = split_text(text, chunk_size=80, overlap=10)
    for c in chunks:
        assert not c.startswith(" ")


def test_empty_text_returns_empty_list():
    assert split_text("", chunk_size=512, overlap=50) == []
