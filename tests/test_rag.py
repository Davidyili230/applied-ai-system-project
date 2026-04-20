"""Tests for KnowledgeBase RAG retrieval and confidence scoring."""

from ai_assistant import KnowledgeBase


def _kb_with_docs(**docs: str) -> KnowledgeBase:
    """Return a KnowledgeBase pre-loaded with the provided {stem: content} docs."""
    kb = KnowledgeBase.__new__(KnowledgeBase)
    kb.docs = dict(docs)
    kb.last_confidence = 0.0
    return kb


def test_rag_confidence_perfect_match():
    """All query tokens present in document → confidence == 1.0."""
    kb = _kb_with_docs(dog_care="feed your dog daily with nutritious food")
    kb.retrieve("feed dog daily")
    assert kb.last_confidence == 1.0


def test_rag_confidence_partial_match():
    """Partial token overlap yields a score strictly between 0 and 1."""
    kb = _kb_with_docs(cat_care="cats need grooming and brushing regularly")
    kb.retrieve("cats need fish")  # 2 of 3 tokens match
    assert 0.0 < kb.last_confidence < 1.0


def test_rag_confidence_no_match_returns_empty():
    """Zero token overlap → confidence == 0.0 and retrieve returns empty string."""
    kb = _kb_with_docs(cat_care="cats need grooming")
    result = kb.retrieve("saltwater aquarium fish")
    assert result == ""
    assert kb.last_confidence == 0.0
