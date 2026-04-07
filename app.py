import pandas as pd
import streamlit as st

from config import Settings
from services.file_service import FileService
from services.sentiment_analysis import SentimentService
from services.analysis_service import AnalysisService
from services.tiktok_scraper_service import TikTokScraperService
from charts.chart_service import ChartService

from db.database import Base, engine, get_session
from db.repositories.analysis_run_repository import AnalysisRunRepository
from db.repositories.analysis_result_repository import AnalysisResultRepository


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
tiktok_scraper_service = TikTokScraperService()

# -------------------------
# SESSION STATE
# -------------------------
if "input_df" not in st.session_state:
    st.session_state["input_df"] = None

if "raw_preview_df" not in st.session_state:
    st.session_state["raw_preview_df"] = None

if "source_file_name" not in st.session_state:
    st.session_state["source_file_name"] = None

if "input_source_type" not in st.session_state:
    st.session_state["input_source_type"] = "Upload file"

if "active_run_id" not in st.session_state:
    st.session_state["active_run_id"] = None


st.title("🤖 AI sentiment Analysis MVP")
st.caption(
    f"Upload a CSV/Excel file or scrape TikTok comments and analyze sentiment using the '{Settings.COMMENT_COLUMN}' column."
)
st.caption(
    "Each comment will be classified as positive, neutral, or negative, and a brief reason for the classification will be provided."
)

with st.sidebar:
    st.header("MVP scope")
    st.write("✅ Upload file")
    st.write("✅ Scrape TikTok comments")
    st.write("✅ Analyse comments")
    st.write("✅ Positive / Neutral / Negative")
    st.write("✅ Overall summary")
    st.write("✅ Save results in database")
    st.write("❌ Trend spotting")
    st.write("❌ Engagement analysis")

# -------------------------
# VÆLG DATAKILDE
# -------------------------
source_type = st.radio(
    "Choose input source",
    ["Upload file", "TikTok URL"],
    horizontal=True,
    key="input_source_type"
)

# -------------------------
# UPLOAD FILE FLOW
# -------------------------
if source_type == "Upload file":
    uploaded_file = st.file_uploader(
        "Upload your CSV or Excel file",
        type=["csv", "xls", "xlsx"]
    )

    if uploaded_file is not None:
        try:
            raw_df = file_service.load_file(uploaded_file)
            df = file_service.normalize_comments(raw_df)

            st.session_state["raw_preview_df"] = raw_df
            st.session_state["input_df"] = df
            st.session_state["source_file_name"] = uploaded_file.name

        except Exception as e:
            st.error(f"Error loading file: {e}")

# -------------------------
# TIKTOK FLOW
# -------------------------
elif source_type == "TikTok URL":
    tiktok_url = st.text_input(
        "Paste TikTok video URL",
        placeholder="https://www.tiktok.com/@username/video/1234567890"
    )

    if st.button("Scrape TikTok comments"):
        if not tiktok_url.strip():
            st.warning("Please enter a TikTok URL.")
        else:
            try:
                with st.spinner("Opening browser and scraping comments..."):
                    raw_df = tiktok_scraper_service.scrape_to_dataframe(
                        video_url=tiktok_url,
                        comment_column=Settings.COMMENT_COLUMN
                    )

                df = file_service.normalize_comments(raw_df)

                st.session_state["raw_preview_df"] = raw_df
                st.session_state["input_df"] = df
                st.session_state["source_file_name"] = tiktok_url

            except Exception as e:
                st.error(f"Error scraping TikTok comments: {e}")

# -------------------------
# VIS DATA FRA SESSION STATE
# -------------------------
stored_raw_df = st.session_state.get("raw_preview_df")
stored_df = st.session_state.get("input_df")
stored_source_file_name = st.session_state.get("source_file_name")

if stored_raw_df is not None:
    if source_type == "TikTok URL":
        st.subheader("Scraped comments preview")
    else:
        st.subheader("Raw data preview")

    st.dataframe(stored_raw_df.head(1100), use_container_width=True)

if stored_df is not None:
    st.subheader("Comments ready for analysis")
    st.write(f"Rows with valid comments: **{len(stored_df)}**")

# -------------------------
# ANALYSE FLOW
# -------------------------
if stored_df is not None:
    if len(stored_df) == 0:
        st.warning(
            f"No valid comments found in the '{Settings.COMMENT_COLUMN}' column. "
            "Please check your input."
        )
    else:
        if st.button("Run sentiment analysis", type="primary"):
            if not sentiment_service.is_ready():
                st.error("Missing OPENAI_API_KEY in your .env file.")
            else:
                session = get_session()

                analysis_run_repo = AnalysisRunRepository(session)
                analysis_result_repo = AnalysisResultRepository(session)

                analysis_service = AnalysisService(
                    sentiment_service=sentiment_service,
                    analysis_run_repo=analysis_run_repo,
                    analysis_result_repo=analysis_result_repo,
                )

                progress_bar = st.progress(0.0)

                run_id, results = analysis_service.run_analysis(
                    df=stored_df,
                    source_file=stored_source_file_name,
                    progress_callback=progress_bar.progress
                )

                progress_bar.empty()
                session.close()

                st.session_state["active_run_id"] = run_id

# -------------------------
# VIS SENESTE ANALYSE
# -------------------------
active_run_id = st.session_state.get("active_run_id")

if active_run_id is not None:
    st.divider()
    st.subheader("Latest analysis")

    session = get_session()
    analysis_result_repo = AnalysisResultRepository(session)

    db_df = analysis_result_repo.fetch_results_for_run_as_dataframe(active_run_id)

    if not db_df.empty:
        # -------------------------
        # SUMMARY
        # -------------------------
        st.subheader("Summary")

        total_count = len(db_df)
        positive_count = (db_df["sentiment"] == "positive").sum()
        neutral_count = (db_df["sentiment"] == "neutral").sum()
        negative_count = (db_df["sentiment"] == "negative").sum()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Text Analyzed", total_count)
        col2.metric("Positive", positive_count)
        col3.metric("Neutral", neutral_count)
        col4.metric("Negative", negative_count)

        if negative_count > positive_count and negative_count > neutral_count:
            overall_label = "Overall Negative"
        elif positive_count > negative_count and positive_count > neutral_count:
            overall_label = "Overall Positive"
        else:
            overall_label = "Overall Mixed / Neutral"

        st.info(overall_label)

        # -------------------------
        # SENTIMENT DISTRIBUTION
        # -------------------------
        st.subheader("Sentiment distribution")

        sentiment_counts = (
            db_df["sentiment"]
            .value_counts()
            .reindex(["positive", "neutral", "negative"], fill_value=0)
        )

        chart_df = sentiment_counts.reset_index()
        chart_df.columns = ["Sentiment", "Count"]

        st.bar_chart(chart_df.set_index("Sentiment"))

        # -------------------------
        # MOST NEGATIVE COMMENTS
        # -------------------------
        negative_df = db_df[db_df["sentiment"] == "negative"][["comment_text", "reason"]].copy()

        if not negative_df.empty:
            st.subheader("Most negative comments")
            st.dataframe(
                negative_df.rename(columns={
                    "comment_text": "Comments",
                    "reason": "reason"
                }),
                use_container_width=True
            )

        # -------------------------
        # DETAILED RESULTS
        # -------------------------
        st.subheader("Result of latest analysis")
        st.dataframe(
            db_df.rename(columns={
                "row_index": "#",
                "comment_text": "Comments",
                "sentiment": "sentiment",
                "reason": "reason",
                "model_name": "model_name",
                "created_at": "created_at",
            }),
            use_container_width=True
        )

        # -------------------------
        # DOWNLOAD CSV
        # -------------------------
        csv_data = db_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download results as CSV",
            data=csv_data,
            file_name=f"analysis_run_{active_run_id}.csv",
            mime="text/csv"
        )

    else:
        st.write("No results found for the latest run.")

    session.close()