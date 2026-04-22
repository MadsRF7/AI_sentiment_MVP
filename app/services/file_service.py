import pandas as pd  # for data manipulation
from app.core.config import Settings  # for configuration management


# FileService class is responsible for handling file operations such as loading, normalizing, and converting data.
class FileService:
    @staticmethod
    def load_file(uploaded_file) -> pd.DataFrame:
        """Load CSV or Excel-file into a DataFrame."""
        file_name = uploaded_file.name.lower()

        if file_name.endswith(".csv"):
            return pd.read_csv(uploaded_file)
        if file_name.endswith(".xlsx") or file_name.endswith(".xls"):
            return pd.read_excel(uploaded_file)

        raise ValueError("Unsupported file type. Please upload a CSV or Excel file.")

    # For normalization, we need to ensure that the required column exists and filter out rows with empty comments.
    # This will help improve the accuracy of sentiment analysis by ensuring we only analyze valid comments.
    @staticmethod
    def normalize_comments(df: pd.DataFrame) -> pd.DataFrame:
        """Keep only rows with non-empty comments and ensure required column exists."""
        required_column = Settings().COMMENT_COLUMN

        if required_column not in df.columns:
            raise ValueError(f"Missing required column: '{required_column}'")

        clean_df = df.copy()
        clean_df[required_column] = (
            clean_df[required_column].astype(str).fillna("").str.strip()
        )
        clean_df = clean_df[clean_df[required_column] != ""].reset_index(drop=True)

        return clean_df

    # For converting the DataFrame to CSV format, we can use the built-in `to_csv` method of pandas.
    # This will allow us to easily export the processed data for download or further analysis.
    @staticmethod
    def convert_df_to_csv(df: pd.DataFrame) -> bytes:
        return df.to_csv(index=False).encode("utf-8")
