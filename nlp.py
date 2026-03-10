from transformers import pipeline

class SentimentAnalyzer:
    def __init__(self):
        # Downloads ~700MB on first run, then cached locally
        self._pipeline = pipeline(
            "text-classification",
            model="nlptown/bert-base-multilingual-uncased-sentiment",
        )

    def get_score(self, text: str) -> float:
        result = self._pipeline(text, truncation=True, max_length=512)[0]
        # Label format is "N stars" where N is 1-5
        # Map to [-1.0, 1.0]: 1->-1.0, 3->0.0, 5->1.0
        stars = int(result["label"][0])
        return (stars - 3) / 2.0
