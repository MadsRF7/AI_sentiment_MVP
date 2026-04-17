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

from textwrap import dedent
from typing import Optional


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

if "active_run_id" not in st.session_state:
    st.session_state["active_run_id"] = None


# -------------------------
# HELPERS
# -------------------------
def safe_percent(count: int, total: int) -> int:
    if total == 0:
        return 0
    return round((count / total) * 100)

from typing import Optional

def render_scrape_status(
    container,
    message: str,
    count: Optional[int] = None,
    is_success: bool = False,
):
    count_html = ""
    if count is not None:
        count_label = "comments collected" if is_success else "comments collected so far"
        count_html = f"<div class='scrape-status-count'>{count} {count_label}</div>"

    box_class = "scrape-status-box success" if is_success else "scrape-status-box"

    container.markdown(
        f"""
        <div class="{box_class}">
            <div class="scrape-status-message">{message}</div>
            {count_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

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

    safe_username = str(username).replace("<", "&lt;").replace(">", "&gt;")
    safe_text = str(text).replace("<", "&lt;").replace(">", "&gt;")

    html = f"""
    <div class="comment-card-v2 {config['card_class']}">
        <div class="comment-card-inner">
            <div class="comment-icon {config['icon_class']}">
                <span>{config['emoji']}</span>
            </div>
            <div class="comment-content">
                <div class="comment-username">@{safe_username}</div>
                <div class="comment-text">{safe_text}</div>
                <div class="sentiment-badge {config['badge_class']}">{config['label']}</div>
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_detailed_results_table(df: pd.DataFrame):
    if df is None or df.empty:
        st.info("No detailed results to show.")
        return

    def esc(value):
        if pd.isna(value):
            return ""
        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def sentiment_badge(value):
        sentiment = str(value).lower().strip()

        badge_class = {
            "positive": "results-sentiment-positive",
            "neutral": "results-sentiment-neutral",
            "negative": "results-sentiment-negative",
        }.get(sentiment, "results-sentiment-default")

        return f'<span class="results-sentiment-badge {badge_class}">{esc(value)}</span>'

    render_df = df.rename(
        columns={
            "row_index": "#",
            "comment_text": "Comments",
            "sentiment": "Sentiment",
            "reason": "Reason",
            "created_at": "Date analyzed",
        }
    ).copy()

    desired_columns = ["#", "Comments", "Sentiment", "Reason", "Date analyzed"]
    existing_columns = [col for col in desired_columns if col in render_df.columns]
    render_df = render_df[existing_columns]

    rows_html = []
    for _, row in render_df.iterrows():
        row_html = "<tr>"

        for col in existing_columns:
            value = row[col]

            if col == "Sentiment":
                cell_html = sentiment_badge(value)
            else:
                cell_html = esc(value)

            extra_class = ""
            if col == "#":
                extra_class = " col-index"
            elif col == "Comments":
                extra_class = " col-comments"
            elif col == "Reason":
                extra_class = " col-reason"
            elif col == "Model":
                extra_class = " col-model"
            elif col == "Created at":
                extra_class = " col-created"

            row_html += f'<td class="{extra_class}">{cell_html}</td>'

        row_html += "</tr>"
        rows_html.append(row_html)

    header_html = "".join([f"<th>{esc(col)}</th>" for col in existing_columns])
    body_html = "".join(rows_html)

    table_html = f"""
    <div class="results-table-card">
        <div class="results-table-scroll">
            <table class="results-table-custom">
                <thead>
                    <tr>{header_html}</tr>
                </thead>
                <tbody>
                    {body_html}
                </tbody>
            </table>
        </div>
    </div>
    """

    st.markdown(table_html, unsafe_allow_html=True)


# -------------------------
# HERO
# -------------------------
st.markdown(
    """
    <div style="text-align:center; padding: 30px 0 10px 0;">
        <div class="hero-badge">AI-Powered Sentiment Analysis</div>
        <div class="hero-title">
            Understand what your<br>
            <span class="accent">TikTok audience really thinks</span>
        </div>
        <div class="hero-subtitle">
            Paste any TikTok video URL and instantly analyze comments
            to uncover emotional insights, trends, and audience sentiment.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        """
        <div class="section-card step-card">
            <h4 style="margin-top:0;">1. Paste URL</h4>
            <p>Automatically extract comments from any TikTok video URL with author details and timestamps.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        """
        <div class="section-card step-card">
            <h4 style="margin-top:0;">2. Fetch comments</h4>
            <p style="margin-bottom:0;">Wait for browser to open, solve CAPTCHA, and comments will be scraped automatically</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        """
        <div class="section-card step-card">
            <h4 style="margin-top:0;">3. AI Analysis</h4>
            <p style="margin-bottom:0;">Classify comments as positive, neutral, or negative with a reason for each classification</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        """
        <div class="section-card step-card">
            <h4 style="margin-top:0;">4. Get Insights</h4>
            <p style="margin-bottom:0;">Review summary, sort by sentiment, and download the result as a CSV-file</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -------------------------
# INPUT CARD
# -------------------------
st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)

with st.container():
    input_col, button_col = st.columns([4, 1])

    with input_col:
        tiktok_url = st.text_input(
            "Paste TikTok video URL",
            placeholder="https://www.tiktok.com/@username/video/1234567890",
            label_visibility="collapsed",
        )

    with button_col:
        analyze_scrape_clicked = st.button("Fetch comments", use_container_width=True)

    if analyze_scrape_clicked:
        if not tiktok_url.strip():
            st.warning("Please enter a TikTok URL.")
        else:
            try:
                # 👇 Status UI container
                status_placeholder = st.empty()

                # 👇 Initial besked
                render_scrape_status(status_placeholder, "Opening TikTok video...")

                # 👇 Callback fra scraper
                def update_scrape_status(message, count=None):
                    render_scrape_status(status_placeholder, message, count)

                # 👇 Kør scraping (NU med live status)
                raw_df, comment_count = tiktok_scraper_service.scrape_to_dataframe(
                    video_url=tiktok_url,
                    comment_column=Settings.COMMENT_COLUMN,
                    status_callback=update_scrape_status,
                )

                df = file_service.normalize_comments(raw_df)

                st.session_state["raw_preview_df"] = raw_df
                st.session_state["input_df"] = df
                st.session_state["source_file_name"] = tiktok_url
                st.session_state["tiktok_comment_count"] = comment_count

                # 👇 Final status (i stedet for spinner-success)
                render_scrape_status(
                    status_placeholder,
                    "Comments collected and ready for analysis",
                    len(df),
                    is_success=True,
                )

            except Exception as e:
                st.error(f"Error scraping TikTok comments: {e}")


# -------------------------
# SESSION DATA
# -------------------------
stored_raw_df = st.session_state.get("raw_preview_df")
stored_df = st.session_state.get("input_df")
stored_source_file_name = st.session_state.get("source_file_name")

if stored_df is not None:
    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
    st.subheader("Comments ready for analysis")
    st.write(f"Number of comments scraped: **{len(stored_df)}**")

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
                    st.markdown(
                        """
                        <div class="success-banner">
                            Sentiment analysis completed
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
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
                        <h3 style="margin:0;">PREVIEW OF COMMENTS</h3>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                preview_df = db_df[["comment_text", "sentiment"]].copy().head(4)
                demo_usernames = ["user_happy", "user_neutral", "user_critical", "user_fan"]

                if not preview_df.empty:
                    for idx, (_, row) in enumerate(preview_df.iterrows()):
                        comment_text = str(row["comment_text"]).strip()
                        sentiment = str(row["sentiment"]).lower().strip()
                        username = demo_usernames[idx] if idx < len(demo_usernames) else f"user_{idx + 1}"
                        render_comment_card(username, comment_text, sentiment)
                elif stored_raw_df is not None and not stored_raw_df.empty:
                    preview_only = stored_raw_df.head(4).copy()
                    comment_col = Settings.COMMENT_COLUMN

                    if comment_col in preview_only.columns:
                        fallback_sentiments = ["positive", "neutral", "negative", "positive"]

                        for idx, (_, row) in enumerate(preview_only.iterrows()):
                            comment_text = str(row[comment_col]).strip()
                            username = demo_usernames[idx] if idx < len(demo_usernames) else f"user_{idx + 1}"
                            sentiment = fallback_sentiments[idx] if idx < len(fallback_sentiments) else "neutral"
                            render_comment_card(username, comment_text, sentiment)

            tiktok_total = st.session_state.get("tiktok_comment_count") or total_count

            # -------------------------
            # RIGHT: RESULT CARD
            # -------------------------
            with right_col:
                st.markdown(
                    dedent("""
                    <div class="section-card neon-orange preview-panel-header">
                        <div class="panel-eyebrow">▥</div>
                        <h3 style="margin:0;">SENTIMENT ANALYSIS SUMMARY</h3>
                    </div>
                    """),
                    unsafe_allow_html=True,
                )

                result_html = dedent(f"""
                <div class="section-card neon-orange results-panel-v2">
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
                """)

                st.markdown(result_html, unsafe_allow_html=True)

                metric_col1, metric_col2 = st.columns(2)

                with metric_col1:
                    st.markdown(
                        dedent(f"""
                        <div class="stat-tile stat-tile-blue">
                            <div class="stat-tile-label">TOTAL COMMENTS ON TIKTOK.COM</div>
                            <div class="stat-tile-value">{tiktok_total:,}</div>
                        </div>
                        """),
                        unsafe_allow_html=True,
                    )

                with metric_col2:
                    st.markdown(
                        dedent(f"""
                        <div class="stat-tile stat-tile-pink">
                            <div class="stat-tile-label">COMMENTS SCRAPED & ANALYZED</div>
                            <div class="stat-tile-value">{total_count:,}</div>
                        </div>
                        """),
                        unsafe_allow_html=True,
                    )

            # -------------------------
            # LOWER SECTION
            # -------------------------
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            st.subheader("Detailed results")
            sort_option = st.selectbox(
            "Sort by sentiment",
            ["Default", "Positive", "Neutral", "Negative"],
            )

            sorted_df = db_df.copy()

            if sort_option != "Default":
                # prioriter valgt sentiment øverst
                sorted_df["sort_key"] = sorted_df["sentiment"].apply(
                    lambda x: 0 if x == sort_option.lower() else 1
                )
                sorted_df = sorted_df.sort_values(by="sort_key").drop(columns=["sort_key"])
            render_detailed_results_table(sorted_df)

            csv_data = sorted_df.to_csv(index=False).encode("utf-8")

            st.markdown("<div class='download-btn-wrapper'>", unsafe_allow_html=True)

            st.download_button(
                label="Download results as CSV",
                data=csv_data,
                file_name=f"analysis_run_{active_run_id}.csv",
                mime="text/csv",
                use_container_width=False,
            )

            st.markdown("</div>", unsafe_allow_html=True)

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
            <h3 style="margin-top:0;">Comment Scraper</h3>
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