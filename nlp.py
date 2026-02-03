from textblob import TextBlob

class SentimentAnalyzer:
    # get_score inputs a string and outputs its "sentiment" score
    def get_score(self, text:str) -> float:
        # returns value within [-1.0, 1.0]
        return TextBlob(text).sentiment.polarity # type: ignore
