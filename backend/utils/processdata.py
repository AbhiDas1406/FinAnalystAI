import pandas as pd

def extract_csv_metadata_and_sample(file_path):
    """
    Reads a CSV file and extracts its metadata and a sample of 5 rows.

    Args:
        file_path (str): Path to the CSV file.

    Returns:
        dict: A dictionary containing metadata and a sample of 5 rows.
    """
    try:
        df = pd.read_csv(file_path)
        metadata = {
            "columns": list(df.columns),
            "num_rows": len(df),
            "num_columns": len(df.columns),
            "dtypes": df.dtypes.apply(lambda x: str(x)).to_dict(),
            "missing_values": df.isnull().sum().to_dict()
        }
        sample = df.head(5).to_dict(orient="records")
        return {
            "metadata": metadata,
            "sample_rows": sample
        }
    except Exception as e:
        return {
            "error": str(e)
        }
