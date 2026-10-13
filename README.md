# TalentLens AI — Resume Screening Website

## Folder structure
```text
TalentLens_AI_Website/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── app.js
```

## Run in VS Code
1. Extract the ZIP and open the `TalentLens_AI_Website` folder in VS Code.
2. Open Terminal → New Terminal.
3. (Recommended) Create a virtual environment:
   - Windows: `python -m venv .venv`
   - Windows PowerShell: `.venv\Scripts\Activate.ps1`
4. Install dependencies:
   `python -m pip install -r requirements.txt`
5. Start the website:
   `python app.py`
6. Open `http://127.0.0.1:5000` in your browser.

## Resume file types
- PDF, DOCX, TXT: supported text extraction.
- PNG, JPG, JPEG, WEBP: OCR using Tesseract.

### To enable image OCR on Windows
The Python package `pytesseract` is only a connector; the Tesseract OCR program must also be installed. Install Tesseract OCR for Windows, then if it is not automatically detected, add its install folder to PATH. Restart the terminal and run the app again. If image OCR isn't set up, PDFs, DOCX, and TXT still work.

## How scoring works
- Resume strength checks common sections, contact information, and measurable-result signals.
- Career-role coverage counts matching curated skill terms.
- Job match blends TF-IDF text similarity with shared-term coverage.

These are prototype heuristics, not validated hiring assessments or probabilities of getting hired. They can miss synonyms, context, and actual proficiency. Do not use these scores as the sole basis for employment decisions.

## Privacy
This demo processes uploads in memory and does not save resumes to a database or upload them to a third-party AI service. A production deployment needs appropriate security, retention, consent, and privacy controls.
