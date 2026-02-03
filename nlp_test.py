from textblob import TextBlob

class SentimentAnalyzer:
    # get_score inputs a string and outputs its "sentiment" score
    def get_score(self, text:str) -> float:
        # returns value within [-1.0, 1.0]
        return TextBlob(text).sentiment.polarity # type: ignore
    
if __name__ == "__main__":
    analyzer = SentimentAnalyzer()

    good_text = "The waiter was very quick and the food was amazing!"
    bad_text = "The waiter was very slow and the food was disgusting!"

    print(f"Review: '{good_text}'")
    print(f"Score: {analyzer.get_score(good_text)}")

    print("-"*30)

    print(f"Review: '{bad_text}'")
    print(f"Score: {analyzer.get_score(bad_text)}")