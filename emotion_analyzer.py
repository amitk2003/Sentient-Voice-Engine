"""
Emotion Analyzer Module
=======================
Combines VADER sentiment analysis with TextBlob for granular emotion detection.
Supports 7 emotional categories with intensity scaling.
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
import re


class EmotionAnalyzer:
    """
    Multi-layered emotion analyzer that combines VADER and TextBlob
    to detect nuanced emotions with intensity scaling.
    
    Emotions detected:
    - happy, excited, calm, neutral, concerned, frustrated, sad
    """

    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()

        # Keywords that hint at specific emotions
        self.emotion_keywords = {
            "excited": [
                "amazing", "incredible", "fantastic", "awesome", "wonderful",
                "excellent", "outstanding", "brilliant", "thrilled", "ecstatic",
                "wow", "unbelievable", "phenomenal", "spectacular", "extraordinary",
                "best ever", "love it", "can't wait", "so excited", "dream come true"
            ],
            "happy": [
                "happy", "glad", "pleased", "good", "nice", "great", "enjoy",
                "delighted", "cheerful", "joyful", "satisfied", "thankful",
                "grateful", "blessed", "wonderful", "content", "smile"
            ],
            "calm": [
                "okay", "fine", "alright", "understand", "noted", "acknowledged",
                "peace", "serene", "tranquil", "relaxed", "steady", "composed",
                "balanced", "settled", "comfortable", "at ease"
            ],
            "concerned": [
                "worry", "worried", "concern", "concerned", "anxious", "unsure",
                "hesitant", "uncertain", "doubt", "doubtful", "nervous", "uneasy",
                "apprehensive", "troubled", "bothered", "wondering"
            ],
            "surprised": [
                "surprised", "shocked", "unexpected", "didn't expect", "what",
                "really", "no way", "seriously", "oh my", "whoa", "astonished",
                "stunned", "startled", "taken aback", "blown away"
            ],
            "frustrated": [
                "frustrated", "annoyed", "irritated", "angry", "furious",
                "outraged", "terrible", "horrible", "awful", "disgusting",
                "unacceptable", "ridiculous", "pathetic", "worst", "hate",
                "fed up", "sick of", "enough", "can't stand", "useless"
            ],
            "sad": [
                "sad", "unhappy", "disappointed", "depressed", "miserable",
                "heartbroken", "devastated", "lonely", "hopeless", "gloomy",
                "sorrowful", "regret", "unfortunate", "tragic", "loss",
                "crying", "tears", "painful", "hurt", "broken"
            ],
            "inquisitive": [
                "how", "why", "what", "when", "where", "who", "which",
                "could you", "would you", "can you", "is it", "do you",
                "tell me", "explain", "wondering", "curious", "question"
            ]
        }

    def analyze(self, text: str) -> dict:
        """
        Analyze text and return emotion classification with intensity.
        
        Returns:
            dict with keys:
            - emotion: str (primary emotion label)
            - intensity: float (0.0 to 1.0)
            - confidence: float (0.0 to 1.0)
            - vader_scores: dict (raw VADER scores)
            - textblob_scores: dict (polarity, subjectivity)
            - all_emotions: dict (scores for each emotion)
        """
        if not text or not text.strip():
            return self._default_result()

        # Get VADER scores
        vader_scores = self.vader.polarity_scores(text)

        # Get TextBlob scores
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity      # -1 to 1
        subjectivity = blob.sentiment.subjectivity  # 0 to 1

        # Compute keyword-based emotion scores
        keyword_scores = self._keyword_analysis(text.lower())

        # Combine analyses to determine emotion
        emotion, intensity, confidence, all_emotions = self._classify_emotion(
            vader_scores, polarity, subjectivity, keyword_scores, text
        )

        return {
            "emotion": emotion,
            "intensity": round(intensity, 3),
            "confidence": round(confidence, 3),
            "vader_scores": {k: round(v, 3) for k, v in vader_scores.items()},
            "textblob_scores": {
                "polarity": round(polarity, 3),
                "subjectivity": round(subjectivity, 3)
            },
            "all_emotions": {k: round(v, 3) for k, v in all_emotions.items()}
        }

    def _keyword_analysis(self, text: str) -> dict:
        """Score each emotion based on keyword presence."""
        scores = {}
        words = set(re.findall(r'\b\w+\b', text))

        for emotion, keywords in self.emotion_keywords.items():
            # Check for single-word keywords
            single_word_matches = sum(1 for kw in keywords if kw in words)
            # Check for multi-word phrases
            phrase_matches = sum(1 for kw in keywords if ' ' in kw and kw in text)
            total = single_word_matches + phrase_matches * 1.5
            scores[emotion] = min(total / 3.0, 1.0)  # Normalize

        return scores

    def _classify_emotion(self, vader: dict, polarity: float,
                          subjectivity: float, keyword_scores: dict,
                          text: str) -> tuple:
        """
        Combine all signals to classify emotion.
        Returns (emotion, intensity, confidence, all_emotion_scores).
        """
        compound = vader["compound"]

        # Initialize emotion scores
        emotion_scores = {
            "happy": 0.0,
            "excited": 0.0,
            "calm": 0.0,
            "neutral": 0.0,
            "concerned": 0.0,
            "surprised": 0.0,
            "inquisitive": 0.0,
            "frustrated": 0.0,
            "sad": 0.0
        }

        # --- Positive emotions ---
        if compound > 0.05:
            if compound > 0.6:
                emotion_scores["excited"] += compound * 0.8
                emotion_scores["happy"] += compound * 0.4
            elif compound > 0.3:
                emotion_scores["happy"] += compound * 0.8
                emotion_scores["excited"] += compound * 0.3
            else:
                emotion_scores["happy"] += compound * 0.5
                emotion_scores["calm"] += 0.3

        # --- Negative emotions ---
        elif compound < -0.05:
            neg_strength = abs(compound)
            if neg_strength > 0.6:
                emotion_scores["frustrated"] += neg_strength * 0.7
                emotion_scores["sad"] += neg_strength * 0.4
            elif neg_strength > 0.3:
                emotion_scores["sad"] += neg_strength * 0.6
                emotion_scores["frustrated"] += neg_strength * 0.3
                emotion_scores["concerned"] += neg_strength * 0.2
            else:
                emotion_scores["concerned"] += neg_strength * 0.5
                emotion_scores["sad"] += neg_strength * 0.3

        # --- Neutral ---
        else:
            emotion_scores["neutral"] += 0.5
            emotion_scores["calm"] += 0.3

        # Check for question marks → inquisitive boost
        question_count = text.count("?")
        if question_count > 0:
            emotion_scores["inquisitive"] += min(0.4 + question_count * 0.15, 0.8)

        # Check for exclamation marks → intensity/excitement boost
        exclaim_count = text.count("!")
        if exclaim_count > 0:
            boost = min(exclaim_count * 0.1, 0.4)
            if compound > 0:
                emotion_scores["excited"] += boost
            else:
                emotion_scores["frustrated"] += boost

        # Check for ALL CAPS words → intensity boost
        caps_words = len(re.findall(r'\b[A-Z]{2,}\b', text))
        if caps_words > 0:
            boost = min(caps_words * 0.08, 0.3)
            if compound > 0:
                emotion_scores["excited"] += boost
            elif compound < 0:
                emotion_scores["frustrated"] += boost

        # Incorporate keyword scores
        for emotion, kw_score in keyword_scores.items():
            if emotion in emotion_scores:
                emotion_scores[emotion] += kw_score * 0.6

        # Normalize scores
        max_score = max(emotion_scores.values())
        if max_score > 0:
            # Softly normalize
            for k in emotion_scores:
                emotion_scores[k] = emotion_scores[k] / (max_score + 0.01)

        # Find primary emotion
        primary_emotion = max(emotion_scores, key=emotion_scores.get)
        primary_score = emotion_scores[primary_emotion]

        # Calculate intensity (0 to 1)
        intensity = min(abs(compound) + subjectivity * 0.3 + primary_score * 0.2, 1.0)

        # If emotion is neutral/calm, reduce intensity
        if primary_emotion in ("neutral", "calm"):
            intensity = max(intensity * 0.5, 0.1)

        # Confidence based on agreement between signals
        confidence = self._compute_confidence(vader, polarity, keyword_scores, primary_emotion)

        return primary_emotion, intensity, confidence, emotion_scores

    def _compute_confidence(self, vader: dict, polarity: float,
                            keyword_scores: dict, emotion: str) -> float:
        """Compute confidence based on agreement between analysis methods."""
        signals = []

        compound = vader["compound"]

        # Signal 1: VADER and TextBlob polarity agreement
        if (compound > 0 and polarity > 0) or (compound < 0 and polarity < 0) or \
           (abs(compound) < 0.1 and abs(polarity) < 0.1):
            signals.append(0.8)
        else:
            signals.append(0.4)

        # Signal 2: Keyword support
        kw_score = keyword_scores.get(emotion, 0)
        signals.append(0.5 + kw_score * 0.5)

        # Signal 3: VADER strength
        signals.append(min(abs(compound) + 0.3, 1.0))

        return sum(signals) / len(signals)

    def _default_result(self) -> dict:
        """Return default neutral result for empty input."""
        return {
            "emotion": "neutral",
            "intensity": 0.0,
            "confidence": 0.0,
            "vader_scores": {"neg": 0, "neu": 1, "pos": 0, "compound": 0},
            "textblob_scores": {"polarity": 0, "subjectivity": 0},
            "all_emotions": {
                "happy": 0, "excited": 0, "calm": 0, "neutral": 1,
                "concerned": 0, "surprised": 0, "inquisitive": 0,
                "frustrated": 0, "sad": 0
            }
        }


# Quick test
if __name__ == "__main__":
    analyzer = EmotionAnalyzer()
    
    test_texts = [
        "This is the best news ever! I'm so thrilled and excited!",
        "I'm really worried about the deadline approaching.",
        "The weather is okay today.",
        "This is absolutely terrible and unacceptable!",
        "I feel so sad and lonely today...",
        "How does this system work? Can you explain?",
        "WOW! I can't believe this happened! AMAZING!",
        "I'm not sure if this will work out.",
    ]

    for text in test_texts:
        result = analyzer.analyze(text)
        print(f"\nText: {text}")
        print(f"  Emotion: {result['emotion']} | Intensity: {result['intensity']} | Confidence: {result['confidence']}")
