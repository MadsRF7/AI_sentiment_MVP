import pandas as pd
import streamlit as st
from pathlib import Path

from config import Settings
from services.file_service import FileService
from services.sentiment_analysis import SentimentService
from services.analysis_service import AnalysisService
from services.tiktok_scraper_service import TikTokScraperService
from charts.chart_service import ChartService

from db.database import Base, engine, get_session
from db.repositories.analysis_run_repository import AnalysisRunRepository
from db.repositories.analysis_result_repository import AnalysisResultRepository


# -------------------------
# PAGE CONFIG
# -------------------------
st.set_page_config(
    page_title=Settings.PAGE_TITLE,
    page_icon=Settings.PAGE_ICON,
    layout=Settings.LAYOUT,
)

# -------------------------
# LOAD CSS
# -------------------------
def load_css():
    css_path = Path(__file__).parent / "styles.css"

    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    else:
        st.error(f"styles.css blev ikke fundet: {css_path}")


load_css()


# -------------------------
# DB INIT
# -------------------------
Base.metadata.create_all(bind=engine)

# -------------------------
# SERVICES
# -------------------------
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
    st.session_state["input_source_type"] = "TikTok URL"

if "active_run_id" not in st.session_state:
    st.session_state["active_run_id"] = None


# -------------------------
# HELPERS
# -------------------------
def safe_percent(count: int, total: int) -> int:
    if total == 0:
        return 0
    return round((count / total) * 100)


def render_comment_card(username: str, text: str, sentiment: str):
    sentiment = str(sentiment).lower().strip()

    config = {
        "positive": {
            "card_class": "comment-positive-v2",
            "icon_class": "comment-icon-positive",
            "badge_class": "sentiment-badge-positive",
            "emoji": "☺",
            "label": "Positive",
        },
        "neutral": {
            "card_class": "comment-neutral-v2",
            "icon_class": "comment-icon-neutral",
            "badge_class": "sentiment-badge-neutral",
            "emoji": "•",
            "label": "Neutral",
        },
        "negative": {
            "card_class": "comment-negative-v2",
            "icon_class": "comment-icon-negative",
            "badge_class": "sentiment-badge-negative",
            "emoji": "☹",
            "label": "Negative",
        },
    }.get(
        sentiment,
        {
            "card_class": "comment-neutral-v2",
            "icon_class": "comment-icon-neutral",
            "badge_class": "sentiment-badge-neutral",
            "emoji": "•",
            "label": "Neutral",
        },
    )

    safe_text = str(text).replace("<", "&lt;").replace(">", "&gt;")
    safe_username = str(username).replace("<", "&lt;").replace(">", "&gt;")

    html = f"""
    <div class="comment-card-v2 {config['card_class']}">
        <div class="comment-card-inner">
            <div class="comment-icon {config['icon_class']}">
                <span>{config['emoji']}</span>
            </div>

            <div class="comment-content">
                <div class="comment-username">@{safe_username}</div>
                <div class="comment-text">"{safe_text}"</div>
                <div class="sentiment-badge {config['badge_class']}">
                    {config['label']}
                </div>
            </div>
        </div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


# -------------------------
# HERO
# -------------------------
st.markdown(
    """
    <div style="text-align:center; padding: 18px 0 10px 0;">
        <div class="hero-badge">AI-Powered Sentiment Analysis</div>
        <div class="hero-title">
            Understand what your<br>
            <span class="accent">TikTok audience really thinks</span>
        </div>
        <div class="hero-subtitle">
            Paste any TikTok video URL or upload a file and instantly analyze comments
            to uncover emotional insights, trends, and audience sentiment.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# GAME PLAN
# -------------------------
st.markdown(
    """
    <div class="ui-card" style="margin-top: 24px; margin-bottom: 18px;">
        <h3 style="text-align:center; margin:0;">GAME PLAN</h3>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        """
        <div class="section-card">
            <h4 style="margin-top:0;">1. Paste URL</h4>
            <p style="margin-bottom:0;">Insert any TikTok video link</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        """
        <div class="section-card">
            <h4 style="margin-top:0;">2. Fetch comments</h4>
            <p style="margin-bottom:0;">Collect comments from TikTok or file upload</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        """
        <div class="section-card">
            <h4 style="margin-top:0;">3. AI Analysis</h4>
            <p style="margin-bottom:0;">Classify comments as positive, neutral, or negative</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        """
        <div class="section-card">
            <h4 style="margin-top:0;">4. Get Insights</h4>
            <p style="margin-bottom:0;">Review summary, sentiment split, and download CSV</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -------------------------
# INPUT SOURCE
# -------------------------
st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)

try:
    source_type = st.segmented_control(
        "Input source",
        options=["TikTok URL", "Upload file"],
        default="TikTok URL",
        key="input_source_type",
    )
except AttributeError:
    source_type = st.radio(
        "Input source",
        ["TikTok URL", "Upload file"],
        horizontal=True,
        key="input_source_type",
    )


# -------------------------
# INPUT CARD
# -------------------------
with st.container():
    st.markdown('<div class="ui-card">', unsafe_allow_html=True)

    if source_type == "TikTok URL":
        input_col, button_col = st.columns([4, 1])

        with input_col:
            tiktok_url = st.text_input(
                "Paste TikTok video URL",
                placeholder="https://www.tiktok.com/@username/video/1234567890",
                label_visibility="collapsed",
            )

        with button_col:
            analyze_scrape_clicked = st.button("Analyze →", use_container_width=True)

        if analyze_scrape_clicked:
            if not tiktok_url.strip():
                st.warning("Please enter a TikTok URL.")
            else:
                try:
                    with st.spinner("Opening browser and scraping comments..."):
                        raw_df = tiktok_scraper_service.scrape_to_dataframe(
                            video_url=tiktok_url,
                            comment_column=Settings.COMMENT_COLUMN,
                        )

                    df = file_service.normalize_comments(raw_df)

                    st.session_state["raw_preview_df"] = raw_df
                    st.session_state["input_df"] = df
                    st.session_state["source_file_name"] = tiktok_url
                    st.success("Comments fetched successfully.")
                except Exception as e:
                    st.error(f"Error scraping TikTok comments: {e}")

    else:
        uploaded_file = st.file_uploader(
            "Upload your CSV or Excel file",
            type=["csv", "xls", "xlsx"],
        )

        if uploaded_file is not None:
            try:
                raw_df = file_service.load_file(uploaded_file)
                df = file_service.normalize_comments(raw_df)

                st.session_state["raw_preview_df"] = raw_df
                st.session_state["input_df"] = df
                st.session_state["source_file_name"] = uploaded_file.name
                st.success(f"Loaded file: {uploaded_file.name}")
            except Exception as e:
                st.error(f"Error loading file: {e}")

    st.markdown("</div>", unsafe_allow_html=True)


# -------------------------
# SESSION DATA
# -------------------------
stored_raw_df = st.session_state.get("raw_preview_df")
stored_df = st.session_state.get("input_df")
stored_source_file_name = st.session_state.get("source_file_name")

if stored_df is not None:
    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
    st.subheader("Comments ready for analysis")
    st.write(f"Rows with valid comments: **{len(stored_df)}**")

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
                try:
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
                        progress_callback=progress_bar.progress,
                    )

                    progress_bar.empty()
                    st.session_state["active_run_id"] = run_id
                    st.success("Sentiment analysis completed.")
                finally:
                    session.close()


# -------------------------
# LATEST ANALYSIS
# -------------------------
active_run_id = st.session_state.get("active_run_id")

if active_run_id is not None:
    st.divider()

    session = get_session()
    analysis_result_repo = AnalysisResultRepository(session)

    try:
        db_df = analysis_result_repo.fetch_results_for_run_as_dataframe(active_run_id)

        if not db_df.empty:
            total_count = len(db_df)
            positive_count = (db_df["sentiment"] == "positive").sum()
            neutral_count = (db_df["sentiment"] == "neutral").sum()
            negative_count = (db_df["sentiment"] == "negative").sum()

            positive_pct = safe_percent(positive_count, total_count)
            neutral_pct = safe_percent(neutral_count, total_count)
            negative_pct = safe_percent(negative_count, total_count)

            if negative_count > positive_count and negative_count > neutral_count:
                overall_label = "NEGATIVE"
            elif positive_count > negative_count and positive_count > neutral_count:
                overall_label = "POSITIVE"
            else:
                overall_label = "MIXED / NEUTRAL"

            left_col, right_col = st.columns([1, 1])

            # -------------------------
            # LEFT: COMMENT PREVIEW
            # -------------------------
            with left_col:
                st.markdown(
                    """
                    <div class="section-card neon-green preview-panel-header">
                        <div class="panel-eyebrow">◫</div>
                        <h3 style="margin:0;">TIKTOK VIDEO COMMENTS</h3>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                preview_df = db_df[["comment_text", "sentiment"]].copy().head(4)
                demo_usernames = ["user_happy", "user_neutral", "user_critical", "user_fan"]

                if not preview_df.empty:
                    for idx, (_, row) in enumerate(preview_df.iterrows()):
                        comment_text = str(row["comment_text"]).strip()[:140]
                        sentiment = str(row["sentiment"]).lower().strip()
                        username = demo_usernames[idx] if idx < len(demo_usernames) else f"user_{idx + 1}"
                        render_comment_card(username, comment_text, sentiment)

                elif stored_raw_df is not None and not stored_raw_df.empty:
                    preview_only = stored_raw_df.head(4).copy()
                    comment_col = Settings.COMMENT_COLUMN

                    if comment_col in preview_only.columns:
                        fallback_sentiments = ["positive", "neutral", "negative", "positive"]

                        for idx, (_, row) in enumerate(preview_only.iterrows()):
                            comment_text = str(row[comment_col]).strip()[:140]
                            username = demo_usernames[idx] if idx < len(demo_usernames) else f"user_{idx + 1}"
                            sentiment = fallback_sentiments[idx] if idx < len(fallback_sentiments) else "neutral"
                            render_comment_card(username, comment_text, sentiment)

                with st.expander("Show raw preview table"):
                    if stored_raw_df is not None:
                        st.dataframe(stored_raw_df.head(200), use_container_width=True)
                    else:
                        st.info("No raw preview data available.")

            # -------------------------
            # RIGHT: RESULT CARD
            # -------------------------
            with right_col:
                sentiment_html = f"""
                <div class="section-card neon-orange results-panel-v2">
                    <div class="panel-eyebrow">▥</div>
                    <h3 style="margin:0;">SENTIMENT ANALYSIS RESULTS</h3>

                    <div class="metric-big">
                        <div style="font-size:12px; opacity:.95; font-weight:800; letter-spacing:.05em;">
                            OVERALL SENTIMENT
                        </div>
                        <div style="font-size:34px; line-height:1.05; margin-top:8px; font-weight:900;">
                            {overall_label}
                        </div>
                        <div style="font-size:13px; margin-top:8px; font-weight:700;">
                            ↗ {positive_pct}% Positive sentiment
                        </div>
                    </div>

                    <div style="margin-bottom:7px; font-weight:800; font-size:14px;">
                        Positive <span style="float:right;">{positive_pct}%</span>
                    </div>
                    <div style="height:11px; background:#31476f; border-radius:999px; overflow:hidden; margin-bottom:14px;">
                        <div style="width:{positive_pct}%; height:100%; background:#20df82;"></div>
                    </div>

                    <div style="margin-bottom:7px; font-weight:800; font-size:14px;">
                        Neutral <span style="float:right;">{neutral_pct}%</span>
                    </div>
                    <div style="height:11px; background:#31476f; border-radius:999px; overflow:hidden; margin-bottom:14px;">
                        <div style="width:{neutral_pct}%; height:100%; background:#f5b942;"></div>
                    </div>

                    <div style="margin-bottom:7px; font-weight:800; font-size:14px;">
                        Negative <span style="float:right;">{negative_pct}%</span>
                    </div>
                    <div style="height:11px; background:#31476f; border-radius:999px; overflow:hidden; margin-bottom:6px;">
                        <div style="width:{negative_pct}%; height:100%; background:#ff586d;"></div>
                    </div>
                </div>
                """

                st.markdown(sentiment_html, unsafe_allow_html=True)

                metric_col1, metric_col2 = st.columns(2)

                with metric_col1:
                    st.markdown(
                        f"""
                        <div class="stat-tile stat-tile-blue">
                            <div class="stat-tile-label">TOTAL COMMENTS</div>
                            <div class="stat-tile-value">{total_count:,}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with metric_col2:
                    st.markdown(
                        f"""
                        <div class="stat-tile stat-tile-pink">
                            <div class="stat-tile-label">ANALYZED</div>
                            <div class="stat-tile-value">{total_count:,}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            # -------------------------
            # LOWER SECTION
            # -------------------------
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            st.subheader("Detailed results")

            st.dataframe(
                db_df.rename(
                    columns={
                        "row_index": "#",
                        "comment_text": "Comments",
                        "sentiment": "Sentiment",
                        "reason": "Reason",
                        "model_name": "Model",
                        "created_at": "Created at",
                    }
                ),
                use_container_width=True,
            )

            csv_data = db_df.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="Download results as CSV",
                data=csv_data,
                file_name=f"analysis_run_{active_run_id}.csv",
                mime="text/csv",
            )

            negative_df = db_df[db_df["sentiment"] == "negative"][["comment_text", "reason"]].copy()

            if not negative_df.empty:
                st.markdown("<div style='margin-top: 22px;'></div>", unsafe_allow_html=True)
                st.subheader("Most negative comments")
                st.dataframe(
                    negative_df.rename(
                        columns={
                            "comment_text": "Comments",
                            "reason": "Reason",
                        }
                    ),
                    use_container_width=True,
                )

        else:
            st.info("No results found for the latest run.")
    finally:
        session.close()


# -------------------------
# FEATURES
# -------------------------
st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
st.markdown(
    "<h2 style='text-align:center;'>POWERFUL FEATURES</h2>",
    unsafe_allow_html=True,
)

f1, f2, f3 = st.columns(3)

with f1:
    st.markdown(
        """
        <div class="feature-card feature-blue">
            <h3 style="margin-top:0;">TikTok Comments Scraper</h3>
            <p>Automatically extract comments from any TikTok video URL with author details and timestamps.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with f2:
    st.markdown(
        """
        <div class="feature-card feature-green">
            <h3 style="margin-top:0;">Sentiment Analysis</h3>
            <p>AI classifies each comment as positive, neutral, or negative with detailed reasoning for accurate insights.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with f3:
    st.markdown(
        """
        <div class="feature-card feature-pink">
            <h3 style="margin-top:0;">Analysis Summary</h3>
            <p>Review visual reports with sentiment distribution, overall mood, and downloadable CSV results.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )