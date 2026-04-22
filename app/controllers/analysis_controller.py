def render_analysis_eta(container, message: str):
    container.markdown(
        f"""
        <div class="analysis-eta-text">
            {message}
        </div>
        """,
        unsafe_allow_html=True,
    )

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
