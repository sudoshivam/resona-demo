import io
import pandas as pd


def papers_to_excel(rows: list) -> io.BytesIO:
    df = pd.DataFrame(rows)
    output = io.BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)
    return output
