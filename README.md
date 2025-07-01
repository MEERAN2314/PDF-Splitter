# PDF Agent Splitter

A powerful tool for extracting specific pages from PDF documents.  This project uses a backend API and a Streamlit frontend.

## Project Structure

- `backend/`: Contains the FastAPI backend server.
- `frontend/`: Contains the Streamlit frontend application.
- `requirements.txt`: Lists project dependencies.

## Features

- **Single File Processing:** Extract specific pages or page ranges.
- **Batch Processing:** Process multiple PDFs simultaneously.
- **PDF Metadata Viewer:** View title, author, and creation dates.
- **Text Extraction:** Extract text content from PDFs.


## Installation

1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd pdf-agent-splitter
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate  # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Start the backend server:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

2. Start the Streamlit frontend in a separate terminal:
   ```bash
   cd frontend
   streamlit run app.py
   ```

3. Access the application at `http://localhost:8501`.


## API Endpoints (Backend)

- `/upload`: Upload and analyze a PDF file.
- `/split`: Extract pages from a PDF.
- `/batch-process`: Process multiple PDFs.
- `/download/{filename}`: Download processed files.


## Configuration

The application can be configured via a `.env` file in the `backend` directory.  See the `.env.example` file for details.


## License

[MIT License](LICENSE)


## Contributing

See the [CONTRIBUTING.md](CONTRIBUTING.md) file for details.
