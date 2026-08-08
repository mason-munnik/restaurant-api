from transformers import pipeline


class SentimentAnalyzer:
    # Small, fast-on-CPU BERT variant fine-tuned for binary pos/neg
    # sentiment; also the default model behind
    # transformers.pipeline("sentiment-analysis").
    MODEL_NAME = "distilbert-base-uncased-finetuned-sst-2-english"

    def __init__(self):
        # Loaded once here; main.py creates a single module-level
        # `analyzer` instance, so weights load once per process.
        self._pipeline = pipeline(
            "sentiment-analysis",
            model=self.MODEL_NAME,
            tokenizer=self.MODEL_NAME,
            device=-1,  # force CPU
        )

    # get_score inputs a string and outputs its "sentiment" score
    def get_score(self, text: str) -> float:
        # returns a signed polarity score in [-1.0, 1.0], matching the
        # contract TextBlob used to have. Unlike TextBlob's continuous
        # polarity, this is a forced binary classifier, so scores cluster
        # near the picked class's confidence rather than near 0.
        if text is None or not text.strip():
            raise ValueError("text cannot be empty")

        result = self._pipeline(text, truncation=True, max_length=512)[0]
        sign = 1.0 if result["label"] == "POSITIVE" else -1.0
        return sign * result["score"]
