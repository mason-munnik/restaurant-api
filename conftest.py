import nlp


def _fake_pipeline_factory(*args, **kwargs):
    def fake_pipeline(text, **kwargs):
        return [{"label": "POSITIVE", "score": 0.99}]
    return fake_pipeline


# main.py builds `analyzer = SentimentAnalyzer()` at import time, which would
# otherwise download/load real BERT weights the moment any test imports it.
nlp.pipeline = _fake_pipeline_factory
