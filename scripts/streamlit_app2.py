
import streamlit as st
import pandas as pd
import fitz
import os
from localStoragePy import localStoragePy
from datetime import datetime
import zipfile
from io import BytesIO


fitz.TOOLS.set_small_glyph_heights(True)
ls = localStoragePy('tom_rw-multi-scope-bid-scanner', 'json')
st.set_page_config(page_title="RW Multi-Scope Bid Scanner", page_icon=None, layout="centered", initial_sidebar_state="auto", menu_items=None)

KEYWORDS = [
    "chain", "link", "ornamental", "fenc", "gate", "operator", "wood", "steel", "bollard", "barrier", "wedge", "crash", "turnstile", "temporary", "rail"
]
START_TIME = None
END_TIME = None


class Updating_Text:
    def __init__(self, text : str):
        self.container = st.empty()
        self.text = text
        self.container = st.code(body=self.text, language="markdown", line_numbers=False)
    
    def update(self, text : str, newline : bool = True):
        with self.container.container():
            if newline:
                self.container = st.code(self.text + "\n" + text, language="markdown", line_numbers=False)
                self.text = self.text + "\n" + text
            else:
                self.container = st.code(self.text + text, language="markdown", line_numbers=False)
                self.text = self.text + text

def save_excel(data, filename):
    df = pd.DataFrame(data, columns=["Filename", "Keyword", "Count", "Pages"])
    df.to_excel(filename, index=False)
    return filename

# Find keyword data from PDF text and save as 2d array
def keys_in_pdf(doc, pdf_name, keywords):
    try:
        keyword_data = {keyword: {"count": 0, "pages": []}
                        for keyword in keywords}
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

        pdf.save(f"highlighted_{pdf_name}")
        pdf.close()
        csv_data = [[pdf_name, keyword, data["count"], data["pages"]]
                    for keyword, data in keyword_data.items() if data["count"] > 0]

        return csv_data
    except Exception as err:
        st.error(f"Failed to process {pdf_name}: {err}")
        return []

def create_zip(files : list, prefix : str = ""):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for file in files:
            file = prefix + file
            zip_file.write(file, os.path.basename(file))
    return zip_buffer.getvalue()


st.title("RW Multi-Scope Bid Scanner")

uploaded_files = st.file_uploader(
    label="Select files to scan:",
    accept_multiple_files=True,
    type=["pdf"],
    # label_visibility="collapsed"
)

use_standard_keys = st.toggle("Use standard keywords")

if use_standard_keys:
    predefined_keys = st.multiselect(
        label="Select keywords:",
        options=KEYWORDS,
        default=KEYWORDS,
        label_visibility="collapsed",
        on_change=print(ls.getItem("standard_keys"))
    )

keyword_input = st.text_input(
    label="Enter additional keywords separated by commas:",
    placeholder="thing 1, item 2, other"
)

if st.button("Scan PDFs"):
    START_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if uploaded_files and (keyword_input or use_standard_keys):
        cur_keywords = []
        if keyword_input:
            cur_keywords = [keyword.strip() for keyword in keyword_input.split(',')]
        if use_standard_keys:
            cur_keywords.extend(predefined_keys)
        
        all_pdfs = []
        all_csv_data = []

        proc_output = Updating_Text(f"STARTED PROCESS at {START_TIME}")

        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name
            file_data = uploaded_file.read()
            proc_output.update(f"Processing {file_name}")

            # Process PDF file
            csv_data = keys_in_pdf(file_data, file_name, cur_keywords)
            all_csv_data.extend(csv_data)
            all_pdfs.append(file_name)

        END_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        proc_output.update(f"ENDED PROCESS at {END_TIME}")

        if all_csv_data:
            csv_file = save_excel(all_csv_data, "output.xlsx")
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

        zip_file = create_zip(all_pdfs, "highlighted_")
        st.download_button(
            label="Download all PDFs",
            data=zip_file,
            file_name="all_files.zip",
            mime="application/zip"
        )

        st.write("Individual PDF downloads:")
        for pdf in all_pdfs:
            with open(f"highlighted_{pdf}", "rb") as data:
                st.download_button(
                    label=f"Download {pdf}",
                    data=data,
                    file_name=f"highlighted_{pdf}",
                    mime="application/pdf"
                )
            os.remove(f"highlighted_{pdf}")
    else:
        st.error("Please upload files and provide keywords.")
