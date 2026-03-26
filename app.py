import os
import json
from io import BytesIO

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
import altair as alt


load_dotenv()

# --------------
# MVP configuration
# --------------
st.set_page_config(
    page_title="AI sentiment Analysis MVP",
    page_icon="🤖",
    layout="wide",
)

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

# --------------
# Helper functions
# --------------
REQUIRED_COLUMN = "Comment ID"

def load_file(uploaded_file) -> pd.DataFrame:
    """Load CSV or Excel-file into a DataFrame."""
    file_name = uploaded_file.name.lower()
    if file_name.endswith('.csv'):
        return pd.read_csv(uploaded_file, encoding='utf-8')
    if file_name.endswith(('.xls', '.xlsx')):
        return pd.read_excel(uploaded_file)
    raise ValueError("Unsupported file type. Please upload a CSV or Excel file.")

def normalize_comments(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only rows with non-empty comments and ensure the required column exists."""
    if REQUIRED_COLUMN not in df.columns:
        raise ValueError(f"Missing required column: '{REQUIRED_COLUMN}'")
    
    clean_df = df.copy()
    clean_df[REQUIRED_COLUMN] = clean_df[REQUIRED_COLUMN].astype(str).fillna('').str.strip()
    clean_df = clean_df[clean_df[REQUIRED_COLUMN] != ''].reset_index(drop=True)
    return clean_df

def classify_comment(comment: str) -> dict:
    """Ask the model to classify one comment.
    Returns a dict with:
    - sentiment: positive|neutral|negative
    - reason: short explanation
    """
    if client is None:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    
    # 1st step in prompt engineering: added more detailed instructions and decision rules to improve accuracy and consistency of sentiment classification
    developer_prompt = """
You are a strict sentiment analysis classifier.

Classify each comment into exactly one label:
- positive
- neutral
- negative

Use these rules strictly:

POSITIVE:
- Clear praise, enthusiasm, affection, satisfaction, admiration, or support.
- Includes compliments, excitement, gratitude, or love.

NEUTRAL:
- Factual, observational, informational, curious, or emotionally weak language.
- Questions without hostility are neutral.
- Advice without frustration is neutral.
- Mixed or unclear emotion should default to neutral.

NEGATIVE:
- Clear frustration, hostility, criticism, insult, contempt, mockery, aggression, or annoyance.
- Dismissive or confrontational tone is negative.

Decision rule:
- If the sentiment is ambiguous, choose NEUTRAL.
- Do not infer hidden emotion beyond the words in the comment.
- Do not over-interpret sarcasm unless it is very obvious.

Return valid JSON only in this exact format:
{
    "sentiment": "positive|neutral|negative",
    "reason": "max 15 words"
}


"""

    user_prompt = f"Comment: \"{comment}\""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "developer", "content": developer_prompt}, # 2nd step with prompt engineering: changed from "system" to "developer" to better reflect the role of the prompt 24-03-2026
            {"role": "user", "content": user_prompt}
        ]
    )

    raw_text = response.output_text.strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        # fallback if the model doesn't return valid JSON
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw_text[start:end])
        else:            
            raise ValueError(f"Could not parse model response as JSON: {raw_text}")
        
    sentiment = str(parsed.get("sentiment", "")).lower().strip()
    reason = str(parsed.get("reason", "")).strip()

    if sentiment not in {"positive", "neutral", "negative"}:
        raise ValueError(f"Invalid sentiment returned: {sentiment}")
    
    return {
        "sentiment": sentiment, 
        "reason": reason,
        }

def analyze_comments(df: pd.DataFrame, progress_bar) -> pd.DataFrame:
    results = []
    total = len(df)

    for idx, row in df.iterrows():
        comment = row[REQUIRED_COLUMN]

        try:
            result = classify_comment(comment)
            sentiment = result["sentiment"]
            reason = result["reason"]
        except Exception as e:
            sentiment = "error"
            reason = str(e)

        enriched_row = row.to_dict()
        enriched_row["sentiment"] = sentiment
        enriched_row["reason"] = reason
        results.append(enriched_row)

        progress_bar.progress((idx + 1) / total)

    return pd.DataFrame(results)

def overall_sentiment_label(counts: pd.Series) -> str:
    positive =int(counts.get("positive", 0))
    neutral = int(counts.get("neutral", 0))
    negative = int(counts.get("negative", 0))

    if positive > neutral and positive >= negative:
        return "Overall Positive"
    if negative > neutral and negative >= positive:
        return "Overall Negative"
    return "Overall Neutral"

def convert_df_to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode('utf-8')


# --------------
# UI
# --------------

st.title("🤖 AI sentiment Analysis MVP")
st.caption("Upload a CSV or Excel file with a 'Comments' column to analyze sentiment.")
st.caption("Each comment will be classified as positive, neutral, or negative, and a brief reason for the classification will be provided.")

with st.sidebar:
    st.header("MVP scope")
    st.write("✅ Upload file")
    st.write("✅ Analyse comments")
    st.write("✅ Positive / Neutral / Negative")
    st.write("✅ Overall summary")
    st.write("❌ Trend spotting")
    st.write("❌ Engagement analysis")

uploaded_file = st.file_uploader("Upload your CSV or Excel file", 
type=["csv", "xls", "xlsx"]
)

if uploaded_file is not None:
    try:
        raw_df = load_file(uploaded_file)
        st.subheader("Raw data preview")
        st.dataframe(raw_df.head(1100), use_container_width=True)

        df = normalize_comments(raw_df)

        st.subheader("Comments ready for analysis")
        st.write(f"Rows with valid comments: **{len(df)}**")

        if len(df) == 0:
            st.warning("No valid comments found in the comments column. Please check your file and ensure it has a 'Comments' column with non-empty values.")
        else:
            if st.button("Run sentiment analysis", type="primary"):
                if client is None:
                    st.error("Missing OPENAI_API_KEY in your .env file.")
                else:
                    progress_bar = st.progress(0.0)
                    results_df = analyze_comments(df, progress_bar)
                    progress_bar.empty()

                    valid_results = results_df[
                        results_df["sentiment"].isin(["positive", "neutral", "negative"])
                        ].copy()
                    
                    counts = valid_results["sentiment"].value_counts()

                    total_analyzed = len(valid_results)
                    pos = int(counts.get("positive", 0))
                    neu = int(counts.get("neutral", 0))
                    neg = int(counts.get("negative", 0))

                    st.subheader("Summary")

                    c1, c2, c3, c4 = st.columns(4)

                    c1.metric("Text Analyzed", total_analyzed)

                    c2.markdown(f"""
                    <div style="text-align:center">
                        <p style="margin-bottom:5px;">Positive</p>
                        <h2 style="color:green;">{pos}</h2>
                    </div>
                    """, unsafe_allow_html=True)

                    c3.markdown(f"""
                    <div style="text-align:center">
                        <p style="margin-bottom:5px;">Neutral</p>
                        <h2 style="color:blue;">{neu}</h2>
                    </div>
                    """, unsafe_allow_html=True)

                    c4.markdown(f"""
                    <div style="text-align:center">
                        <p style="margin-bottom:5px;">Negative</p>
                        <h2 style="color:red;">{neg}</h2>
                    </div>
                    """, unsafe_allow_html=True)

                    st.info(overall_sentiment_label(counts))

                    st.subheader("Sentiment distribution")

                    chart_df = pd.DataFrame({
                        "sentiment": ["positive", "neutral", "negative"],
                        "count": [pos, neu, neg]
                    })

                    chart = alt.Chart(chart_df).mark_bar().encode(
                        x=alt.X(
                            "sentiment:N",
                            title="Sentiment",
                            sort=["positive", "neutral", "negative"]  # 👈 vigtig linje
                        ),
                        y=alt.Y("count:Q", title="Count"),
                        color=alt.Color(
                            "sentiment:N",
                            scale=alt.Scale(
                                domain=["positive", "neutral", "negative"],
                                range=["#16a34a", "#2563eb", "#dc2626"]
                            ),
                            legend=None
                        )
                    ).properties(
                        height=400
                    )

                    st.altair_chart(chart, use_container_width=True)

                    st.subheader("Most negative comments")
                    negative_df = results_df[results_df["sentiment"] == "negative"][
                        [REQUIRED_COLUMN, "reason"]
                    ].head(5)

                    if len(negative_df) > 0:
                        st.dataframe(negative_df, use_container_width=True)
                    else:
                        st.write("No negative comments found.")

                    st.subheader("Detailed results")
                    def color_sentiment(val):
                        if val == "positive":
                            return "color: green; font-weight: bold;"
                        elif val == "neutral":
                            return "color: blue; font-weight: bold;"
                        elif val == "negative":
                            return "color: red; font-weight: bold;"
                        return ""

                    styled_df = results_df.style.map(color_sentiment, subset=["sentiment"])

                    st.dataframe(styled_df, use_container_width=True)

                    csv_data = convert_df_to_csv(results_df)
                    st.download_button(
                        label="Download results as CSV",
                        data=csv_data,
                        file_name="sentiment_results.csv",
                        mime="text/csv"
                    )

    except Exception as e:
        st.error(f"Error: {e}")

