import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from utils.processdata import extract_csv_metadata_and_sample

load_dotenv()

def build_prompt(csv_info, user_query, csv_path):
    return f"""
You are an expert Python data analyst. Given the following CSV metadata and sample rows, and the CSV file path, write Python code using pandas (and matplotlib if needed) to answer the user's query.
- The CSV metadata and sample rows are provided below.
- The path to the CSV file is: {csv_path}
- The code should load the data into a pandas DataFrame called 'df' using pd.read_csv and the provided csv_path. Do not generate your own data.
- If the query requires a plot or graph, use matplotlib to generate it and save it as 'output.png'.
- Only output the Python code, and do not include any markdown formatting or code block markers.

CSV Metadata and Sample:
{csv_info}

User Query:
{user_query}
"""

def extract_code_only(text):
    # Remove any code block markers (e.g., ```python ... ```)
    import re
    # Remove triple backtick blocks (with or without python)
    code = re.sub(r"^```(?:python)?\s*|```$", "", text, flags=re.MULTILINE)
    # Remove any leading/trailing whitespace
    return code.strip()

def generate_code_from_query(csv_path, user_query, model_name="gemini-2.5-flash"):
    csv_info = extract_csv_metadata_and_sample(csv_path)
    prompt = build_prompt(csv_info, user_query, csv_path)
    llm = ChatGoogleGenerativeAI(model=model_name)
    response = llm.invoke(prompt)
    code_raw = response.content if hasattr(response, "content") else str(response)
    code = extract_code_only(code_raw)
    return code

def main():
    csv_path = r"C:\Users\subar\OneDrive\Desktop\abhidas\Graphagent\backend\utils\products-1000.csv"
    user_query = "generate a graph displaying histogram of stocks"
    code = generate_code_from_query(csv_path, user_query)
    print("Generated Python code:\n")
    print(code)

if __name__ == "__main__":
    main()