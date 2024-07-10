
import streamlit as st
import pandas as pd
import fitz
import os
from localStoragePy import localStoragePy
from datetime import datetime
import zipfile
from io import BytesIO


fitz.TOOLS.set_small_glyph_heights(True)
ls = localStoragePy("tom_rw-multi-scope-bid-scanner", "json")
st.set_page_config(page_title="RW Multi-Scope Bid Scanner", page_icon="https://avatars.githubusercontent.com/u/154240431?s=400&u=0c23bffefdf0d19a524eb945ac3e3affaa635cdf&v=4", layout="centered", initial_sidebar_state="auto", menu_items=None)

KEYWORDS = [
    "chain", "link", "ornamental", "fenc", "gate", "operator", "wood", "steel", "bollard", "barrier", "wedge", "crash", "turnstile", "temporary", "rail"
]
START_TIME = None
END_TIME = None
RUNNING = False
ERRORS = 0


class Terminal:
    # Instantiates a new text block that can be edited later
    def __init__(self, text : str, lang : str = "markdown"):
        self.container = st.empty()
        self.text = text
        self.lang = lang
        self.last_len = len(text)
        self.container = st.code(body=self.text, language=self.lang, line_numbers=False)
    
    # Adds text to an existing text block
    def update(self, text : str, newline : bool = True):
        with self.container.container():
            if newline:
                self.container = st.code(self.text + "\n" + text, language=self.lang, line_numbers=False)
                self.text = self.text + "\n" + text
            else:
                self.container = st.code(self.text + text, language=self.lang, line_numbers=False)
                self.text = self.text + text
            self.last_len = len(text)
    
    # Replaces the previous text update with this text
    def replace_last(self, text : str, newline : bool = False):
        with self.container.container():
            if newline:
                self.container = st.code(self.text[:-self.last_len] + "\n" + text, language=self.lang, line_numbers=False)
                self.text = self.text[:-self.last_len] + "\n" + text
            else:
                self.container = st.code(self.text[:-self.last_len] + text, language=self.lang, line_numbers=False)
                self.text = self.text[:-self.last_len] + text
            self.last_len = len(text)
    
    # A loading bar [==>] with progress (from 0 to 1) and a total length of segments
    # Must start at 0, which instantiates a new loading bar
    def loading(self, progress: float, total_length: int = 20) -> str:
        # Clamp progress between 0 and 1
        progress = max(0, min(1, progress))
        filled_length = round(total_length * progress)
        
        # Fill loading bar
        if filled_length < total_length:
            bar = "=" * (filled_length - 1)
            bar += ">"
        else:
            bar = "=" * filled_length
        bar = bar.ljust(total_length)
        
        text = f"[{bar}]"

        if self.text[:-self.last_len] + text == self.text:
            return

        with self.container.container():
            if progress == 0:
                self.container = st.code(self.text + "\n" + text, language=self.lang, line_numbers=False)
                self.text = self.text + "\n" + text
            else:
                self.container = st.code(self.text[:-self.last_len] + text, language=self.lang, line_numbers=False)
                self.text = self.text[:-self.last_len] + text
            self.last_len = len(text)

def save_excel(data, filename):
    df = pd.DataFrame(data, columns=["Filename", "Keyword", "Count", "Pages"])
    df.to_excel(filename, index=False)
    return filename

# Find keyword data from PDF text and save as 2d array
def keys_in_pdf(file, doc, pdf_name, keywords, error, load_bar):
    try:
        load_bar.loading(0)
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
            
            load_bar.loading(((page_number - 1) / (len(pdf) - 1)) - 0.1 if len(pdf) > 1 else 0.9)

        pdf.save(f"highlighted_{pdf_name}")
        pdf.close()

        csv_data = [[pdf_name, keyword, data["count"], data["pages"]]
                    for keyword, data in keyword_data.items() if data["count"] > 0]
        
        load_bar.loading(1)
        load_bar.update("Successfully processed file.\n")
        return csv_data
    except Exception as err:
        load_bar.update(f"Failed to process {pdf_name}:\n{err}\n")
        return error + 1

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
        on_change=ls.setItem("standard_keys", ["thing 1", "thing 2"])
    )
    print(ls.getItem("standard_keys"))

keyword_input = st.text_input(
    label="Enter additional keywords separated by commas:",
    placeholder="thing 1, item 2, other"
)

if st.button("Scan PDFs") and not RUNNING:
    START_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    RUNNING = True
    ERRORS = 0

    if not uploaded_files:
        st.toast("Please upload files.")
    if not keyword_input and not use_standard_keys:
        st.toast("Please provide keywords.")
    
    if uploaded_files and (keyword_input or use_standard_keys):
        cur_keywords = []
        if keyword_input:
            cur_keywords = [keyword.strip() for keyword in keyword_input.split(',')]
        if use_standard_keys:
            cur_keywords.extend(predefined_keys)
        
        all_pdfs = []
        all_csv_data = []

        proc_container = st.status("Processing PDFs")
        with proc_container:
            proc_output = Terminal(f"[ STARTED PROCESS at {START_TIME} ]\n", "ini")

            for uploaded_file in uploaded_files:
                file_name = uploaded_file.name
                file_data = uploaded_file.read()
                proc_output.update(f"Processing {file_name}")

                # Process PDF file
                csv_data = keys_in_pdf(uploaded_file, file_data, file_name, cur_keywords, ERRORS, proc_output)
                if type(csv_data) == int:
                    ERRORS += csv_data
                    continue
                all_csv_data.extend(csv_data)
                all_pdfs.append(file_name)
                uploaded_file.close()

            END_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            proc_output.update(f"[ ENDED PROCESS at {END_TIME} ]")

        if ERRORS:
            proc_container.update(state="error")
            st.toast(f"{ERRORS} sheet failed to process; see process log for more details." if ERRORS == 1 else f"{ERRORS} sheets failed to process; see process log for more details.")

        RUNNING = False

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

            zip_file = create_zip(all_pdfs, "highlighted_")
            st.download_button(
                label="Download all PDFs",
                data=zip_file,
                file_name="all_files.zip",
                mime="application/zip"
            )

            with st.expander("Individual PDF downloads"):
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
            st.toast("No keywords found in the uploaded files.")