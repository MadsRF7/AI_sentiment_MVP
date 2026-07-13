import altair as alt  # for data visualization
import pandas as pd


# Service class for building charts based on sentiment analysis results
class ChartService:
    @staticmethod
    def build_sentiment_chart(pos: int, neu: int, neg: int):
        chart_df = pd.DataFrame(
            {"sentiment": ["positive", "neutral", "negative"], "count": [pos, neu, neg]}
        )

        # Build a bar chart using Altair to visualize the sentiment distribution
        chart = (
            alt.Chart(chart_df)
            .mark_bar()
            .encode(
                x=alt.X(
                    "sentiment:N",
                    title="Sentiment",
                    sort=["positive", "neutral", "negative"],
                ),
                y=alt.Y("count:Q", title="Count"),
                color=alt.Color(
                    "sentiment:N",
                    scale=alt.Scale(
                        domain=["positive", "neutral", "negative"],
                        range=["#16a34a", "#2563eb", "#dc2626"],
                    ),
                    legend=None,
                ),
            )
            .properties(height=400)
        )

        return chart
