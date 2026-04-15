import json # for debugging purposes, to print the raw response from the API in a readable format
import pandas as pd # for data manipulation and analysis
from openai import OpenAI
from config import Settings


# SentimentService is responsible for classifying comments into positive, neutral, or negative using the OpenAI API. 
# It checks if the API key is set and provides a method to classify individual comments based on a structured prompt.
class SentimentService:
    def __init__(self):
        if not Settings.OPENAI_API_KEY:
            self.client = None
        else:
            self.client = OpenAI(api_key=Settings.OPENAI_API_KEY)

    def is_ready(self) -> bool:
        return self.client is not None

    def classify_comment(self, comment: str) -> dict:
        """Classify one comment into positive, neutral, or negative."""
        if self.client is None:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        
        developer_prompt = """
You are a strict and context-aware sentiment analysis classifier.

Classify each comment into exactly one label:
- positive
- neutral
- negative

Use these rules strictly:

POSITIVE:
- Clear praise, enthusiasm, affection, satisfaction, admiration, or support.
- Includes compliments, excitement, gratitude, or love.
- Mentions (tagging other users) that indicate engagement or sharing should be considered POSITIVE.

NEUTRAL:
- Factual, observational, informational, curious, or emotionally weak language.
- Questions without hostility are neutral.
- Advice without frustration is neutral.
- Mixed or unclear emotion should default to neutral.
- Comments containing only emojis or very weak signals should be classified as NEUTRAL.

NEGATIVE:
- Clear frustration, hostility, criticism, insult, contempt, mockery, aggression, or annoyance.
- Dismissive or confrontational tone is negative.
- Ignore comments that contain only swear words or pure hate without meaningful context (treat as low-value and classify conservatively).

Decision rules:
- If the sentiment is ambiguous, choose NEUTRAL.
- Do not infer hidden emotion beyond the words in the comment.
- Do not over-interpret sarcasm unless it is very obvious.
- Avoid overly pessimistic interpretations; only classify as NEGATIVE when clear intent is present.
- Focus on meaningful analytical value rather than noise.

Context awareness:
- Consider that comments come from social media (e.g., TikTok), where emojis, mentions, and informal language are common.
- Not all comments are equally meaningful; prioritise intent over surface-level expressions.

Return valid JSON only in this exact format:
{
    "sentiment": "positive|neutral|negative",
    "reason": "max 15 words"
}
"""

# The user prompt includes the comment to be classified, 
# and the developer prompt provides detailed instructions 
# and rules for classification to improve accuracy and consistency.
        user_prompt = f"Comment: \"{comment}\""

        response = self.client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "developer", "content": developer_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        # For debugging: print the raw response from the API in a readable format
        raw_text = response.output_text.strip()

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(raw_text[start:end])
            else:
                raise ValueError(f"Could not parse model response as JSON: {raw_text}")
        
        # Validate the parsed response and ensure it contains the expected keys and values
        sentiment = str(parsed.get("sentiment", "")).lower().strip()
        reason = str(parsed.get("reason", "")).strip()

        if sentiment not in {"positive", "neutral", "negative"}:
            raise ValueError(f"Invalid sentiment returned: {sentiment}")

        return {
            "sentiment": sentiment,
            "reason": reason,
        }
    
    # This method iterates through all comments in the provided DataFrame, 
    # classifies each comment using the classify_comment method, 
    # and enriches the DataFrame with the sentiment and reason for each comment. 
    # It also supports an optional progress callback to track the progress of the analysis.
    def analyze_comments(self, df: pd.DataFrame, progress_callback=None) -> pd.DataFrame:
        """Analyze all comments in the dataframe."""
        results = []
        total = len(df)
        comment_column = Settings.COMMENT_COLUMN

# Iterate through each comment in the DataFrame, classify it, and enrich the row with the sentiment and reason.
        for idx, row in df.iterrows():
            comment = row[comment_column]

            try:
                result = self.classify_comment(comment)
                sentiment = result["sentiment"]
                reason = result["reason"]
            except Exception as e:
                sentiment = "error"
                reason = str(e)

# Enrich the original row with the sentiment and reason, and add it to the results list
            enriched_row = row.to_dict()
            enriched_row["sentiment"] = sentiment
            enriched_row["reason"] = reason
            results.append(enriched_row)
# Update progress if a callback is provided (e.g., to update a progress bar in the UI)
            if progress_callback is not None and total > 0:
                progress_callback((idx + 1) / total)

# After processing all comments, convert the results list into a new DataFrame and return it
        return pd.DataFrame(results)
    
    # This method takes a Series of sentiment counts (e.g., number of positive, neutral, and negative comments)
    # and determines the overall sentiment label based on which sentiment has the highest count.
    @staticmethod
    def overall_sentiment_label(counts: pd.Series) -> str:
        positive = int(counts.get("positive", 0))
        neutral = int(counts.get("neutral", 0))
        negative = int(counts.get("negative", 0))

        if positive > neutral and positive >= negative:
            return "Overall Positive"
        if negative > neutral and negative >= positive:
            return "Overall Negative"
        return "Overall Neutral"
