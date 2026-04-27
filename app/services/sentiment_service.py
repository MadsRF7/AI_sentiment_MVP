import json  # for debugging purposes, to print the raw response from the API in a readable format

import pandas as pd  # for data manipulation and analysis
from openai import OpenAI

from app.core.config import Settings


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
You are a strict, context-aware, and sports-analytical sentiment classifier grounded in fan behaviour theory (Psychological Continuum Model). 

Classify each comment into exactly one label: 
- positive 
- neutral 
- negative 

Additionally, interpret the comment in terms of fan engagement level (PCM): 
- Awareness (low engagement) 
- Attraction (interest) 
- Attachment (emotional connection) 
- Allegiance (loyal commitment)

PCM INTERPRETATION RULES: 
- Awareness → minimal emotion, passive observation 
- Attraction → interest, curiosity, light engagement 
- Attachment → emotional reactions (positive or negative) 
- Allegiance → strong loyalty, repeated engagement, identity-based support


Use these rules strictly:

POSITIVE: 
- Clear support, praise, excitement, or engagement 
- Mentions and sharing indicate engagement
- Strong emotional support indicates Attachment or Allegiance 

NEUTRAL: 
- Observational, informational, or low emotional intensity 
- Emoji-only or weak signals 
- Likely Awareness or Attraction stage

NEGATIVE: 
- Clear frustration or criticism 
- If criticism comes from engaged fans, classify sentiment carefully 
- Criticism from loyal fans may indicate Attachment, not disengagement 


Decision rules: 
- If ambiguous → NEUTRAL 
- Do not over-interpret sarcasm 
- Avoid pessimistic bias 
- Distinguish between disengaged negativity and engaged criticism

Context awareness: 
- Social media (TikTok) 
- Includes humour, rivalry, irony 
- Sports fandom includes emotional investment and identity
Reasoning rules: 
- Explain BOTH sentiment AND PCM level 
- Max 15 words 

Return valid JSON: { "sentiment": "positive|neutral|negative", "pcm_level": "awareness|attraction|attachment|allegiance", "reason": "max 15 words" }
"""

        # The user prompt includes the comment to be classified,
        # and the developer prompt provides detailed instructions
        # and rules for classification to improve accuracy and consistency.
        user_prompt = f'Comment: "{comment}"'

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
        except json.JSONDecodeError as e:
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(raw_text[start:end])
            else:
                raise ValueError(
                    f"Could not parse model response as JSON: {raw_text}"
                ) from e

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
    def analyze_comments(
        self, df: pd.DataFrame, progress_callback=None
    ) -> pd.DataFrame:
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
