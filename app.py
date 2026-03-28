import pandas as pd
import streamlit as st

from config import Settings
from services.file_service import FileService
from services.sentiment_analysis import SentimentService
from services.analysis_service import AnalysisService
from charts.chart_service import ChartService

from db.database import Base, engine, get_session
from db.repositories.video_repository import VideoRepository
from db.repositories.comment_repository import CommentRepository
from db.repositories.sentiment_repository import SentimentRepository
 

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

                    video_repo = VideoRepository(session)
                    comment_repo = CommentRepository(session)
                    sentiment_repo = SentimentRepository(session)

                    analysis_service = AnalysisService(
                        sentiment_service=sentiment_service,
                        video_repo=video_repo,
                        comment_repo=comment_repo,
                        sentiment_repo=sentiment_repo,
                    )

                    progress_bar = st.progress(0.0)

                    results = analysis_service.run_analysis(
                        df=df,
                        source_file=uploaded_file.name,
                        progress_callback=progress_bar.progress
                    )

                    progress_bar.empty()
                    session.close()

                    results_df = pd.DataFrame(results)

        st.divider()
        st.subheader("Saved analyses in database")

        session = get_session()
        sentiment_repo = SentimentRepository(session)
        db_df = sentiment_repo.fetch_analysis_overview_as_dataframe()
        session.close()

        if not db_df.empty:
            st.dataframe(db_df.tail(50), use_container_width=True)
        else:
            st.write("No analyses saved in the database yet.")

    except Exception as e:
        st.error(f"Error: {e}")