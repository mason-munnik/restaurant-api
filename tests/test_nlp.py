import pytest

from app.services.nlp import SentimentAnalyzer


def _stub_pipeline(label, score, calls=None):
    def pipeline(text, **kwargs):
        if calls is not None:
            calls.append((text, kwargs))
        return [{"label": label, "score": score}]

    return pipeline


@pytest.fixture
def analyzer():
    return SentimentAnalyzer()


def test_get_score_positive_text(analyzer):
    analyzer._pipeline = _stub_pipeline("POSITIVE", 0.95)
    assert analyzer.get_score("The food was fantastic!") == 0.95


def test_get_score_negative_text(analyzer):
    analyzer._pipeline = _stub_pipeline("NEGATIVE", 0.87)
    assert analyzer.get_score("The food was terrible.") == -0.87


@pytest.mark.parametrize("label,score", [("POSITIVE", 1.0), ("NEGATIVE", 1.0)])
def test_get_score_result_within_bounds(analyzer, label, score):
    analyzer._pipeline = _stub_pipeline(label, score)
    result = analyzer.get_score("some review text")
    assert -1.0 <= result <= 1.0


def test_get_score_empty_text_raises_value_error(analyzer):
    with pytest.raises(ValueError):
        analyzer.get_score("")


def test_get_score_whitespace_only_text_raises_value_error(analyzer):
    with pytest.raises(ValueError):
        analyzer.get_score("   ")


def test_get_score_calls_pipeline_with_truncation(analyzer):
    calls = []
    analyzer._pipeline = _stub_pipeline("POSITIVE", 0.9, calls=calls)
    analyzer.get_score("some review text")
    assert len(calls) == 1
    _, kwargs = calls[0]
    assert kwargs["truncation"] is True
    assert kwargs["max_length"] == 512
