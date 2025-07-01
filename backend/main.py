# backend/main.py (updated)
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import PyPDF2
import io
import os
from datetime import datetime
import uuid
import json
import zipfile
from fastapi.responses import FileResponse

app = FastAPI(
    title="PDF Agent Splitter API",
    description="API for splitting PDF documents and extracting specific pages",
    version="1.1.0"  # Updated version
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PDFSplitRequest(BaseModel):
    pages: List[int]
    output_format: str = "pdf"  # pdf or separate_pages

class PDFMetadata(BaseModel):
    title: str = None
    author: str = None
    creator: str = None
    producer: str = None
    creation_date: str = None
    modification_date: str = None
    total_pages: int

class PDFSplitResponse(BaseModel):
    status: str
    message: str = None
    download_url: str = None
    metadata: PDFMetadata = None
    extracted_text: str = None
    file_size: str = None

class BatchProcessResponse(BaseModel):
    status: str
    message: str = None
    download_url: str = None
    processed_files: int = 0
    total_files: int = 0
    errors: List[str] = []

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_pdf_metadata(pdf_reader):
    metadata = pdf_reader.metadata
    return PDFMetadata(
        title=metadata.title if metadata else None,
        author=metadata.author if metadata else None,
        creator=metadata.creator if metadata else None,
        producer=metadata.producer if metadata else None,
        creation_date=str(metadata.creation_date) if metadata and metadata.creation_date else None,
        modification_date=str(metadata.modification_date) if metadata and metadata.modification_date else None,
        total_pages=len(pdf_reader.pages)
    )

def extract_text_from_pages(pdf_reader, pages):
    text = ""
    for page_num in pages:
        if 0 < page_num <= len(pdf_reader.pages):
            page = pdf_reader.pages[page_num - 1]
            text += f"=== Page {page_num} ===\n{page.extract_text()}\n\n"
    return text.strip()

def parse_page_selection(pages_str: str, max_pages: int) -> List[int]:
    """Parse page selection string into list of page numbers"""
    page_numbers = []
    for part in pages_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            if start < 1 or end > max_pages:
                raise ValueError(f"Page range {start}-{end} is out of range (1-{max_pages})")
            page_numbers.extend(range(start, end + 1))
        else:
            page_num = int(part)
            if page_num < 1 or page_num > max_pages:
                raise ValueError(f"Page {page_num} is out of range (1-{max_pages})")
            page_numbers.append(page_num)
    
    # Remove duplicates and sort
    return sorted(list(set(page_numbers)))

@app.post("/upload", response_model=PDFSplitResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        # Save the uploaded file temporarily
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
        
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        
        # Read the PDF
        with open(file_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            metadata = get_pdf_metadata(pdf_reader)
            file_size = f"{os.path.getsize(file_path) / 1024:.2f} KB"
        
        return PDFSplitResponse(
            status="success",
            message="PDF uploaded successfully",
            metadata=metadata,
            file_size=file_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/split", response_model=PDFSplitResponse)
async def split_pdf(file: UploadFile = File(...), pages: str = "1", output_format: str = "pdf"):
    try:
        # Read the PDF first to get total pages
        pdf_content = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        total_pages = len(pdf_reader.pages)
        
        # Parse page selection
        page_numbers = parse_page_selection(pages, total_pages)
        
        # Extract metadata
        metadata = get_pdf_metadata(pdf_reader)
        
        # Extract selected pages
        pdf_writer = PyPDF2.PdfWriter()
        extracted_text = ""
        
        for page_num in page_numbers:
            page = pdf_reader.pages[page_num - 1]
            pdf_writer.add_page(page)
            extracted_text += f"=== Page {page_num} ===\n{page.extract_text()}\n\n"
        
        # Prepare output
        output_buffer = io.BytesIO()
        pdf_writer.write(output_buffer)
        output_buffer.seek(0)
        
        # Save the output temporarily for download
        file_id = str(uuid.uuid4())
        output_path = os.path.join(UPLOAD_DIR, f"{file_id}_split.pdf")
        
        with open(output_path, "wb") as f:
            f.write(output_buffer.getvalue())
        
        return PDFSplitResponse(
            status="success",
            message=f"Extracted pages {pages} successfully",
            download_url=f"/download/{file_id}_split.pdf",
            metadata=metadata,
            extracted_text=extracted_text.strip(),
            file_size=f"{len(output_buffer.getvalue()) / 1024:.2f} KB"
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error splitting PDF: {str(e)}")

@app.post("/batch-process", response_model=BatchProcessResponse)
async def batch_process(files: List[UploadFile] = File(...), pages: str = "1", output_format: str = "pdf"):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    batch_id = str(uuid.uuid4())
    zip_filename = f"batch_{batch_id}.zip"
    zip_path = os.path.join(UPLOAD_DIR, zip_filename)
    
    processed_files = 0
    errors = []
    
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in files:
            try:
                if not file.filename.lower().endswith('.pdf'):
                    errors.append(f"Skipped {file.filename}: Not a PDF file")
                    continue
                
                # Process each file
                file_content = await file.read()
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
                total_pages = len(pdf_reader.pages)
                
                try:
                    page_numbers = parse_page_selection(pages, total_pages)
                except ValueError as e:
                    errors.append(f"Skipped {file.filename}: {str(e)}")
                    continue
                
                # Extract selected pages
                pdf_writer = PyPDF2.PdfWriter()
                for page_num in page_numbers:
                    pdf_writer.add_page(pdf_reader.pages[page_num - 1])
                
                # Add to ZIP
                output_buffer = io.BytesIO()
                pdf_writer.write(output_buffer)
                output_filename = f"extracted_{os.path.splitext(file.filename)[0]}.pdf"
                zipf.writestr(output_filename, output_buffer.getvalue())
                processed_files += 1
                
            except Exception as e:
                errors.append(f"Error processing {file.filename}: {str(e)}")
    
    if processed_files == 0:
        os.remove(zip_path)
        raise HTTPException(status_code=400, detail="No files were processed successfully")
    
    return BatchProcessResponse(
        status="success",
        message=f"Processed {processed_files} files",
        download_url=f"/download/{zip_filename}",
        processed_files=processed_files,
        total_files=len(files),
        errors=errors
    )

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path, filename=filename)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)