from typing import Optional

import pandas as pd
import streamlit as st


def render_scrape_status(
    container,
    message: str,
    count: Optional[int] = None,
    is_success: bool = False,
):
    count_html = ""
    if count is not None:
        count_label = (
            "comments collected" if is_success else "comments collected so far"
        )
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


def render_analysis_eta(container, message: str):
    container.markdown(
        f"""
        <div class="analysis-eta-text">
            {message}
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
            str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )

    def sentiment_badge(value):
        sentiment = str(value).lower().strip()

        badge_class = {
            "positive": "results-sentiment-positive",
            "neutral": "results-sentiment-neutral",
            "negative": "results-sentiment-negative",
        }.get(sentiment, "results-sentiment-default")

        return (
            f'<span class="results-sentiment-badge {badge_class}">{esc(value)}</span>'
        )

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

            row_html += f"<td>{cell_html}</td>"

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
