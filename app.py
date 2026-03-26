import pandas as pd
import streamlit as st

from config import Settings
from services.file_service import FileService
from services.sentiment_analysis import SentimentService
from services.analysis_service import AnalysisService
from charts.chart_service import ChartService

from db.database import Base, engine, get_session
from db.repositories.comment_repository import CommentRepository

# Opret tabeller hvis de ikke findes
Base.metadata.create_all(bind=engine)

st.set_page_config(
    page_title=Settings.PAGE_TITLE,
    page_icon=Settings.PAGE_ICON,
    layout=Settings.LAYOUT,
)

file_service = FileService()
sentiment_service = SentimentService()
chart_service = ChartService()

st.title("🤖 AI sentiment Analysis MVP")
st.caption(f"Upload a CSV or Excel file with a '{Settings.COMMENT_COLUMN}' column to analyze sentiment.")
st.caption("Each comment will be classified as positive, neutral, or negative, and a brief reason for the classification will be provided.")

with st.sidebar:
    st.header("MVP scope")
    st.write("✅ Upload file")
    st.write("✅ Analyse comments")
    st.write("✅ Positive / Neutral / Negative")
    st.write("✅ Overall summary")
    st.write("✅ Save results in database")
    st.write("❌ Trend spotting")
    st.write("❌ Engagement analysis")

uploaded_file = st.file_uploader(
    "Upload your CSV or Excel file",
    type=["csv", "xls", "xlsx"]
)

if uploaded_file is not None:
    try:
        raw_df = file_service.load_file(uploaded_file)
        st.subheader("Raw data preview")
        st.dataframe(raw_df.head(1100), use_container_width=True)

        df = file_service.normalize_comments(raw_df)

        st.subheader("Comments ready for analysis")
        st.write(f"Rows with valid comments: **{len(df)}**")

        if len(df) == 0:
            st.warning(
                f"No valid comments found in the '{Settings.COMMENT_COLUMN}' column. "
                "Please check your file."
            )
        else:
            if st.button("Run sentiment analysis", type="primary"):
                if not sentiment_service.is_ready():
                    st.error("Missing OPENAI_API_KEY in your .env file.")
                else:
                    session = get_session()
                    repository = CommentRepository(session)
                    analysis_service = AnalysisService(sentiment_service, repository)

                    progress_bar = st.progress(0.0)

                    results_df = analysis_service.run_analysis(
                        df=df,
                        source_file=uploaded_file.name,
                        progress_callback=progress_bar.progress
                    )

                    progress_bar.empty()
                    session.close()

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
                    c2.metric("Positive", pos)
                    c3.metric("Neutral", neu)
                    c4.metric("Negative", neg)

                    st.info(sentiment_service.overall_sentiment_label(counts))

                    st.subheader("Sentiment distribution")
                    chart = chart_service.build_sentiment_chart(pos, neu, neg)
                    st.altair_chart(chart, use_container_width=True)

                    st.subheader("Most negative comments")
                    negative_df = results_df[results_df["sentiment"] == "negative"][
                        [Settings.COMMENT_COLUMN, "reason"]
                    ].head(5)

                    if len(negative_df) > 0:
                        st.dataframe(negative_df, use_container_width=True)
                    else:
                        st.write("No negative comments found.")

                    st.subheader("Detailed results")

                    def color_sentiment(val):
                        if val == "positive":
                            return "color: green; font-weight: bold;"
                        if val == "neutral":
                            return "color: blue; font-weight: bold;"
                        if val == "negative":
                            return "color: red; font-weight: bold;"
                        return ""

                    styled_df = results_df.style.map(color_sentiment, subset=["sentiment"])
                    st.dataframe(styled_df, use_container_width=True)

                    csv_data = file_service.convert_df_to_csv(results_df)
                    st.download_button(
                        label="Download results as CSV",
                        data=csv_data,
                        file_name="sentiment_results.csv",
                        mime="text/csv"
                    )

        st.divider()
        st.subheader("Saved analyses in database")

        session = get_session()
        repository = CommentRepository(session)
        db_df = repository.fetch_all_as_dataframe()
        session.close()

        if not db_df.empty:
            st.dataframe(db_df.tail(50), use_container_width=True)
        else:
            st.write("No analyses saved in the database yet.")

    except Exception as e:
        st.error(f"Error: {e}")