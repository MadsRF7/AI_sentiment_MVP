import pandas as pd
import streamlit as st

from config import Settings
from services.file_service import FileService
from services.sentiment_analysis import SentimentService
from services.analysis_service import AnalysisService
from charts.chart_service import ChartService

from db.database import Base, engine, get_session
from db.models import AnalysisRun, AnalysisResult
from db.repositories.analysis_run_repository import AnalysisRunRepository
from db.repositories.analysis_result_repository import AnalysisResultRepository
from db.models import AnalysisRun, AnalysisResult
 

# Creates tables if they don't exist
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

                    analysis_run_repo = AnalysisRunRepository(session)
                    analysis_result_repo = AnalysisResultRepository(session)

                    analysis_service = AnalysisService(
                        sentiment_service=sentiment_service,
                        analysis_run_repo=analysis_run_repo,
                        analysis_result_repo=analysis_result_repo,
                    )

                    progress_bar = st.progress(0.0)

                    run_id, results = analysis_service.run_analysis(
                        df=df,
                        source_file=uploaded_file.name,
                        progress_callback=progress_bar.progress
                    )

                    progress_bar.empty()
                    session.close()

                    results_df = pd.DataFrame(results)
                    st.session_state["active_run_id"] = run_id

                    st.divider()
                    st.subheader("Latest analysis")

                    session = get_session()
                    analysis_run_repo = AnalysisRunRepository(session)
                    analysis_result_repo = AnalysisResultRepository(session)

                    active_run_id = st.session_state.get("active_run_id")

                    if active_run_id is None:
                        latest_run = analysis_run_repo.get_latest_completed_run()
                        if latest_run:
                            active_run_id = latest_run.id
                            st.session_state["active_run_id"] = active_run_id

                    if active_run_id is not None:
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

                            # Enkel samlet vurdering
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

                            st.bar_chart(
                                chart_df.set_index("Sentiment")
                            )

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
                    else:
                        st.write("No analyses saved in the database yet.")

                    session.close()

    except Exception as e:
        st.error(f"Error: {e}")