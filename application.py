# from flask import Flask

# application = Flask(__name__)

# @application.route("/")
# def hello_world():
#     return "Hello world!"


import streamlit as st
import pandas as pd
import fitz
from io import BytesIO
import os


fitz.TOOLS.set_small_glyph_heights(True)

st.title('RW Multi-Scope Bid Scanner')

# File uploader
uploaded_files = st.file_uploader('Choose files to scan: ', accept_multiple_files=True, type=["pdf"])

# Keyword input
keyword_input = st.text_input("Enter your keywords separated by commas: ")

# Function to save CSV data locally
def save_csv(data, filename):
    df = pd.DataFrame(data, columns=["Filename", "Keyword", "Count", "Pages"])
    df.to_excel(filename, index=False)
    return filename

# Find keyword data from PDF text and save as 2d array
def keys_in_pdf(doc, pdf_name, keywords):
    try:
        keyword_data = {keyword: {"count": 0, "pages": []} for keyword in keywords}
        pdf = fitz.open(stream=doc, filetype="pdf")

        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text()
            for keyword in keywords:
                # Adding keyword data
                if keyword.lower() in text.lower():
                    keyword_data[keyword]["count"] += text.lower().count(keyword.lower())
                    keyword_data[keyword]["pages"].append(page_number)

                # Highlighting keywords in PDF
                for i in page.search_for(keyword):
                    highlight = page.add_highlight_annot(i)
                    highlight.update()

        pdf.save("highlighted.pdf")
        pdf.close()
        csv_data = [[pdf_name, keyword, data["count"], data["pages"]] for keyword, data in keyword_data.items() if data["count"] > 0]

        return csv_data
    except Exception as err:
        st.error(f"Failed to process {pdf_name}: {err}")
        return []

if st.button("Scan!"):
    if uploaded_files and keyword_input:
        keywords = [keyword.strip() for keyword in keyword_input.split(',')]
        all_csv_data = []

        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name
            file_data = uploaded_file.read()
            st.write(f"Processing {file_name}")

            # Process the PDF file
            csv_data = keys_in_pdf(file_data, file_name, keywords)
            all_csv_data.extend(csv_data)

            # Save highlighted PDF
            with open("highlighted.pdf", "rb") as data:
                st.download_button(
                    label=f"Download highlighted {file_name}",
                    data=data,
                    file_name=f"highlighted_{file_name}",
                    mime="application/pdf"
                )
            os.remove("highlighted.pdf")

        if all_csv_data:
            csv_file = save_csv(all_csv_data, "output.xlsx")
            with open(csv_file, "rb") as data:
                st.download_button(
                    label="Download CSV",
                    data=data,
                    file_name="output.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            os.remove(csv_file)
        else:
            st.info("No keywords found in the uploaded files.")
    else:
        st.error("Please upload files and enter keywords.")