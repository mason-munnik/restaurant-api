from transformers import pipeline

class SentimentAnalyzer:
    def __init__(self):
        # Downloads ~700MB on first run, then cached locally
        self._pipeline = pipeline(
            "text-classification",
            model="nlptown/bert-base-multilingual-uncased-sentiment",
        )

    def get_score(self, text: str) -> int:
        result = self._pipeline(text, truncation=True, max_length=512)[0]
        # Label format is "N stars" where N is 1-5
        return int(result["label"][0])
