# frontend/app.py (updated)
import streamlit as st
import requests
import os
from io import BytesIO
import pandas as pd
import time
import base64
from PIL import Image
import tempfile
import zipfile

# Configuration
BACKEND_URL = "https://pdf-splitter-backend1.onrender.com"
st.set_page_config(page_title="PDF Agent Splitter", page_icon="✂️", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        border: none;
    }
    .stButton>button:hover {
        background-color: #45a049;
        color: white;
    }
    .stFileUploader>div>div>button {
        background-color: #2196F3;
        color: white;
    }
    .stFileUploader>div>div>button:hover {
        background-color: #0b7dda;
        color: white;
    }
    .sidebar .sidebar-content {
        background-color: #f0f2f6;
    }
    .error-message {
        color: #ff4b4b;
        font-size: 0.9rem;
    }
    .success-message {
        color: #4CAF50;
        font-size: 0.9rem;
    }
    </style>
    """, unsafe_allow_html=True)

def display_pdf_preview(pdf_file):
    try:
        # Display PDF preview (first page as image)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_file.getvalue())
            tmp_path = tmp.name
        
        # Convert first page to image
        import fitz  # PyMuPDF
        doc = fitz.open(tmp_path)
        page = doc.load_page(0)
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        st.image(img, caption="First Page Preview", use_column_width=True)
        doc.close()
        os.unlink(tmp_path)
    except Exception as e:
        st.warning(f"Couldn't generate preview: {str(e)}")

def process_batch_files(uploaded_files, page_selection, output_format):
    """Process multiple files through the batch API endpoint"""
    if not uploaded_files:
        st.error("No files selected for batch processing")
        return None
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    files_to_upload = []
    for uploaded_file in uploaded_files:
        files_to_upload.append(("files", (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")))
    
    try:
        status_text.markdown("Uploading and processing files...")
        
        response = requests.post(
            f"{BACKEND_URL}/batch-process",
            files=files_to_upload,
            data={"pages": page_selection, "output_format": output_format},
            timeout=60  # Increased timeout for batch processing
        )
        
        if response.status_code == 200:
            result = response.json()
            progress_bar.progress(100)
            
            if result["processed_files"] > 0:
                status_text.markdown(
                    f"<div class='success-message'>Processed {result['processed_files']} of {result['total_files']} files successfully</div>", 
                    unsafe_allow_html=True
                )
                
                # Show errors if any
                if result["errors"]:
                    with st.expander("Processing Errors", expanded=False):
                        for error in result["errors"]:
                            st.markdown(f"<div class='error-message'>{error}</div>", unsafe_allow_html=True)
                
                # Download button
                download_url = f"{BACKEND_URL}{result['download_url']}"
                response = requests.get(download_url)
                
                if response.status_code == 200:
                    st.download_button(
                        label="Download All as ZIP",
                        data=response.content,
                        file_name=f"pdf_extractions_{int(time.time())}.zip",
                        mime="application/zip"
                    )
                return result
            else:
                status_text.markdown(
                    "<div class='error-message'>No files were processed successfully</div>", 
                    unsafe_allow_html=True
                )
                return None
        else:
            error_detail = response.json().get("detail", "Unknown error")
            status_text.markdown(
                f"<div class='error-message'>Error: {error_detail}</div>", 
                unsafe_allow_html=True
            )
            return None
    
    except Exception as e:
        status_text.markdown(
            f"<div class='error-message'>Error during batch processing: {str(e)}</div>", 
            unsafe_allow_html=True
        )
        return None

def main():
    st.title("✂️ PDF Agent Splitter")
    st.markdown("Extract specific pages from your PDF documents with ease")
    
    with st.sidebar:
        st.header("Settings")
        page_selection = st.text_input("Pages to extract (e.g., 1,3 or 1-5)", "1-2")
        output_format = st.selectbox("Output format", ["pdf"])
        
        st.markdown("---")
        st.markdown("### How to use")
        st.markdown("""
        1. Upload your PDF file(s)
        2. Select pages to extract
        3. Preview the content (single file)
        4. Download the result(s)
        """)
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        This tool allows you to:
        - Extract specific pages from PDFs
        - Process single files or batches
        - Preview PDF content
        - View document metadata
        - Download results as ZIP for batch processing
        """)
    
    tab1, tab2 = st.tabs(["Single File", "Batch Processing"])
    
    with tab1:
        st.subheader("Single PDF Processing")
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", key="single_uploader")
        
        if uploaded_file is not None:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("File Information")
                with st.spinner("Analyzing PDF..."):
                    response = requests.post(
                        f"{BACKEND_URL}/upload",
                        files={"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                    )
                
                if response.status_code == 200:
                    result = response.json()
                    st.success("PDF uploaded successfully!")
                    
                    st.markdown("#### Metadata")
                    metadata = result["metadata"]
                    metadata_df = pd.DataFrame({
                        "Property": ["Title", "Author", "Creator", "Producer", 
                                      "Creation Date", "Modification Date", "Total Pages"],
                        "Value": [
                            metadata["title"] or "N/A",
                            metadata["author"] or "N/A",
                            metadata["creator"] or "N/A",
                            metadata["producer"] or "N/A",
                            metadata["creation_date"] or "N/A",
                            metadata["modification_date"] or "N/A",
                            metadata["total_pages"]
                        ]
                    })
                    st.table(metadata_df)
                    
                    st.markdown(f"**File Size:** {result['file_size']}")
                else:
                    st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
            
            with col2:
                st.subheader("Preview")
                display_pdf_preview(uploaded_file)
            
            st.markdown("---")
            st.subheader("Extract Pages")
            
            if st.button("Extract Selected Pages", key="single_extract"):
                with st.spinner("Extracting pages..."):
                    split_response = requests.post(
                        f"{BACKEND_URL}/split",
                        files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")},
                        data={"pages": page_selection, "output_format": output_format}
                    )
                
                if split_response.status_code == 200:
                    split_result = split_response.json()
                    st.success("Pages extracted successfully!")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### Extracted Content Preview")
                        st.text_area("Text Content", split_result["extracted_text"], height=300, key="single_text")
                    
                    with col2:
                        st.markdown("#### Download")
                        download_url = f"{BACKEND_URL}{split_result['download_url']}"
                        st.markdown(f"**File Size:** {split_result['file_size']}")
                        
                        # Download button
                        response = requests.get(download_url)
                        if response.status_code == 200:
                            st.download_button(
                                label="Download Extracted PDF",
                                data=response.content,
                                file_name=f"extracted_{uploaded_file.name}",
                                mime="application/pdf",
                                key="single_download"
                            )
                        else:
                            st.error("Failed to prepare download")
                else:
                    st.error(f"Error: {split_response.json().get('detail', 'Unknown error')}")
    
    with tab2:
        st.subheader("Batch PDF Processing")
        st.info("Upload multiple PDFs to extract the same pages from all files. Results will be downloaded as a ZIP archive.")
        
        uploaded_files = st.file_uploader(
            "Choose PDF files", 
            type="pdf", 
            accept_multiple_files=True,
            key="batch_uploader"
        )
        
        if uploaded_files:
            st.markdown(f"Selected {len(uploaded_files)} files for processing")
            
            # Show a sample of the first few files
            with st.expander("View selected files", expanded=False):
                file_list = [file.name for file in uploaded_files]
                st.write(pd.DataFrame({"Filename": file_list}))
            
            if st.button("Process All Files", key="batch_process"):
                result = process_batch_files(uploaded_files, page_selection, output_format)
                
                if result:
                    st.balloons()  # Celebration for successful batch processing

if __name__ == "__main__":
    main()