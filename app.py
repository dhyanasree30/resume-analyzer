from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from pypdf import PdfReader
from docx import Document
from PIL import Image
import io
import re
import os

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024  # 12 MB upload limit
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "png", "jpg", "jpeg", "webp"}

ROLE_SKILLS = {
    "Frontend Developer": ["html", "css", "javascript", "react", "vue", "angular", "responsive design", "typescript", "bootstrap"],
    "Backend Developer": ["python", "java", "node.js", "flask", "django", "api", "rest", "sql", "database"],
    "Full Stack Developer": ["html", "css", "javascript", "react", "node.js", "python", "api", "sql", "database"],
    "Data Analyst": ["sql", "excel", "power bi", "tableau", "python", "pandas", "statistics", "visualization", "analytics"],
    "Data Scientist": ["python", "machine learning", "statistics", "pandas", "numpy", "scikit-learn", "tensorflow", "data analysis"],
    "Machine Learning Intern": ["python", "machine learning", "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "statistics"],
    "Data Engineer": ["python", "sql", "etl", "pipeline", "data warehouse", "spark", "airflow", "aws", "azure", "database"],
    "Cloud / DevOps Intern": ["linux", "docker", "kubernetes", "aws", "azure", "cloud", "git", "automation", "terraform"],
    "Java Developer": ["java", "spring", "spring boot", "sql", "oop", "rest api", "hibernate", "maven"],
    "Python Developer": ["python", "flask", "django", "fastapi", "sql", "api", "automation", "pandas"],
    "QA / Test Engineer": ["testing", "test cases", "selenium", "automation", "python", "java", "api testing", "jira"],
    "Cybersecurity Intern": ["networking", "linux", "security", "siem", "penetration testing", "python", "cryptography", "owasp"],
    "UI/UX Design Intern": ["figma", "wireframes", "prototyping", "user research", "ui", "ux", "design systems", "usability"],
    "Business Analyst": ["excel", "sql", "requirements", "documentation", "stakeholders", "power bi", "analysis", "process"],
}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text(file_storage):
    filename = secure_filename(file_storage.filename or "")
    extension = filename.rsplit(".", 1)[-1].lower()
    raw = file_storage.read()
    try:
        if extension == "pdf":
            reader = PdfReader(io.BytesIO(raw))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        if extension == "docx":
            doc = Document(io.BytesIO(raw))
            chunks = [p.text for p in doc.paragraphs]
            for table in doc.tables:
                for row in table.rows:
                    chunks.append(" ".join(cell.text for cell in row.cells))
            return "\n".join(chunks)
        if extension == "txt":
            return raw.decode("utf-8", errors="ignore")
        if extension in {"png", "jpg", "jpeg", "webp"}:
            try:
                import pytesseract
                image = Image.open(io.BytesIO(raw)).convert("RGB")
                return pytesseract.image_to_string(image)
            except ImportError:
                raise ValueError("Image OCR package is missing. Install pytesseract and Pillow, plus the Tesseract OCR program.")
            except Exception as exc:
                raise ValueError("Could not read text from this image. Check that Tesseract OCR is installed and the image is clear.") from exc
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("This file could not be read. Try a text-based PDF, DOCX, TXT, or a clear image.") from exc
    return ""

def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()

def has_term(term, text):
    pattern = r"(?<![a-z0-9])" + re.escape(term.lower()).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
    return bool(re.search(pattern, text.lower()))

def resume_quality(text):
    low = text.lower()
    checks = [
        ("Contact details", bool(re.search(r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b", text)) or bool(re.search(r"\b(?:\+?\d[\d ()-]{8,}\d)\b", text))),
        ("Skills section", any(term in low for term in ["skills", "technical skills", "core competencies"])),
        ("Education section", any(term in low for term in ["education", "academic background", "qualification"])),
        ("Projects or experience", any(term in low for term in ["projects", "experience", "internship", "work history"])),
        ("Certifications or achievements", any(term in low for term in ["certification", "certifications", "achievements", "awards"])),
        ("Measurable results", bool(re.search(r"\b\d+\s?(%|users|customers|hours|days|projects|members|x)\b", low))),
        ("Enough detail", len(text.split()) >= 100),
    ]
    score = round(100 * sum(ok for _, ok in checks) / len(checks))
    faults = [name for name, ok in checks if not ok]
    return score, checks, faults

def get_role_matches(text):
    rows = []
    for role, skills in ROLE_SKILLS.items():
        found = [skill for skill in skills if has_term(skill, text)]
        rows.append({
            "role": role,
            "score": round(100 * len(found) / len(skills)),
            "skills": found,
            "total_skills": len(skills),
        })
    return sorted(rows, key=lambda row: row["score"], reverse=True)

def job_match(resume_text, job_text):
    """Compare a resume with a job description and explain the evidence."""
    resume_lower = resume_text.lower()
    job_lower = job_text.lower()

    all_skills = sorted({
        skill for skills in ROLE_SKILLS.values() for skill in skills
    } | {
        "php", "c", "c++", "c#", "javascript", "typescript", "html", "css",
        "sql", "mysql", "postgresql", "mongodb", "communication",
        "problem solving", "teamwork", "leadership", "figma", "adobe xd",
        "wireframes", "prototyping", "user research", "responsive design",
        "bootstrap", "tailwind", "rest api", "wordpress", "laravel", "oop",
        "git", "agile", "scrum", "accessibility", "usability testing",
        "interaction design", "visual design", "information architecture",
        "design systems", "mockups", "user journey mapping",
    })

    required_skills = [s for s in all_skills if has_term(s, job_lower)]
    matching_skills = [s for s in required_skills if has_term(s, resume_lower)]
    missing_skills = [s for s in required_skills if s not in matching_skills]

    # Qualification evidence: detect education level/field phrases in both texts.
    qualification_patterns = [
        ("Bachelor's degree", r"\b(bachelor'?s?|b\.?tech|b\.?e\.?|b\.?sc|b\.?s\.?)\b"),
        ("Master's degree", r"\b(master'?s?|m\.?tech|m\.?e\.?|m\.?sc|m\.?s\.?)\b"),
        ("Computer Science / IT", r"\b(computer science|information technology|software engineering|computer engineering|it degree)\b"),
        ("Design-related qualification", r"\b(visual communication|interaction design|graphic design|product design|design degree)\b"),
        ("Relevant certification", r"\b(certification|certified|certificate|professional certificate)\b"),
    ]
    job_qualifications = [
        label for label, pattern in qualification_patterns
        if re.search(pattern, job_lower, re.I)
    ]
    resume_qualifications = [
        label for label, pattern in qualification_patterns
        if re.search(pattern, resume_lower, re.I)
    ]
    qualification_matches = [q for q in job_qualifications if q in resume_qualifications]
    qualification_missing = [q for q in job_qualifications if q not in resume_qualifications]

    # Experience evidence: look for years, internships, projects, and work history.
    def years_in(text):
        vals = re.findall(r"\b(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b", text, re.I)
        return max((float(v) for v in vals), default=None)

    job_years = years_in(job_text)
    resume_years = years_in(resume_text)
    job_accepts_freshers = bool(re.search(r"\b(fresher|freshers|entry.level|no experience required|recent graduates?)\b", job_lower))
    resume_has_experience_evidence = bool(re.search(
        r"\b(internship|intern|work experience|professional experience|employment|work history|projects|project experience)\b",
        resume_lower
    ))
    experience_met = (
        job_accepts_freshers
        or job_years is None
        or (resume_years is not None and resume_years >= job_years)
        or (job_years is not None and resume_has_experience_evidence and resume_years is None)
    )
    if job_accepts_freshers:
        experience_reason = "The job description welcomes freshers or entry-level applicants."
    elif job_years is not None and resume_years is not None:
        experience_reason = f"Job asks for about {job_years:g}+ years; resume mentions {resume_years:g} years."
    elif job_years is not None and resume_has_experience_evidence:
        experience_reason = f"Job mentions {job_years:g}+ years. Resume shows projects/internship/work evidence, but does not state a clear number of years."
    elif job_years is not None:
        experience_reason = f"Job mentions {job_years:g}+ years; no clear experience evidence was detected in the resume."
    elif resume_has_experience_evidence:
        experience_reason = "Relevant project, internship, or work-history evidence was found in the resume."
    else:
        experience_reason = "No clear project, internship, or work-history evidence was detected."

    # Skills are the main score; qualification and experience evidence contribute too.
    skill_score = 100 * len(matching_skills) / max(1, len(required_skills)) if required_skills else 50
    qualification_score = (
        100 * len(qualification_matches) / len(job_qualifications)
        if job_qualifications else 70
    )
    experience_score = 100 if experience_met else 35

    # If job description has no recognizable skill list, avoid claiming a precise eligibility score.
    overall_score = round(
        0.65 * skill_score + 0.20 * qualification_score + 0.15 * experience_score
    )
    overall_score = max(0, min(100, overall_score))

    # Eligibility is a transparent guidance label, not an automated hiring decision.
    if overall_score >= 75 and (not qualification_missing or qualification_score >= 50) and experience_met:
        eligibility = "Good alignment"
        eligibility_summary = "The resume appears to meet many of the detected job criteria. Review the evidence and any missing requirements."
    elif overall_score >= 50:
        eligibility = "Partial alignment"
        eligibility_summary = "The resume meets some detected criteria, but one or more skills, qualifications, or experience details need review."
    else:
        eligibility = "Low alignment"
        eligibility_summary = "Few of the detected criteria were found in the resume. Check whether the resume text was extracted correctly and review the missing items."

    details = {
        "skill_score": round(skill_score),
        "qualification_score": round(qualification_score),
        "experience_score": round(experience_score),
        "required_skills": required_skills,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "job_qualifications": job_qualifications,
        "qualification_matches": qualification_matches,
        "qualification_missing": qualification_missing,
        "experience_met": experience_met,
        "experience_reason": experience_reason,
        "resume_years": resume_years,
        "job_years": job_years,
        "eligibility": eligibility,
        "eligibility_summary": eligibility_summary,
    }
    return overall_score, matching_skills, missing_skills, details

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyze-resume", methods=["POST"])
def analyze_resume():
    file = request.files.get("resume")
    if not file or not file.filename:
        return jsonify({"error": "Please upload a resume file first."}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Supported formats: PDF, DOCX, TXT, PNG, JPG, JPEG, and WEBP."}), 400
    try:
        text = clean_text(extract_text(file))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if len(text) < 30:
        return jsonify({"error": "Very little text was found. Try a clearer image or a text-based PDF/DOCX file."}), 400

    strength, checks, faults = resume_quality(text)
    roles = get_role_matches(text)
    words = len(text.split())
    # The value is explicitly a resume completeness/strength indicator, not hiring confidence.
    return jsonify({
        "success": True,
        "filename": secure_filename(file.filename),
        "resume_strength": strength,
        "word_count": words,
        "detected_skills": sorted({skill for role in ROLE_SKILLS.values() for skill in role if has_term(skill, text)}),
        "roles": roles[:10],
        "checks": [{"name": name, "passed": passed} for name, passed in checks],
        "faults": faults,
        "resume_text": text,
        "note": "Resume strength measures document completeness signals. It is not a probability of being hired."
    })

@app.route("/match-job", methods=["POST"])
def match_job():
    data = request.get_json(silent=True) or {}
    resume_text = clean_text(data.get("resume_text", ""))
    job_text = clean_text(data.get("job_description", ""))

    if len(resume_text) < 30:
        return jsonify({"error": "Analyze a resume first."}), 400
    if len(job_text) < 30:
        return jsonify({"error": "Paste a complete job description (at least a few sentences)."}), 400

    score, matching, missing, details = job_match(resume_text, job_text)
    label = "Good alignment" if score >= 75 else ("Partial alignment" if score >= 50 else "Low alignment")

    return jsonify({
        "success": True,
        "score": score,
        "label": label,
        "matching_terms": matching,
        "missing_terms": missing,
        "eligibility": details["eligibility"],
        "eligibility_summary": details["eligibility_summary"],
        "criteria": {
            "skills": {
                "score": details["skill_score"],
                "required": details["required_skills"],
                "matched": details["matching_skills"],
                "missing": details["missing_skills"],
            },
            "qualifications": {
                "score": details["qualification_score"],
                "required": details["job_qualifications"],
                "matched": details["qualification_matches"],
                "missing": details["qualification_missing"],
            },
            "experience": {
                "score": details["experience_score"],
                "met": details["experience_met"],
                "reason": details["experience_reason"],
                "job_years": details["job_years"],
                "resume_years": details["resume_years"],
            },
        },
        "note": "This is a prototype screening aid based on text evidence, not a hiring probability or final eligibility decision. Review the original resume and job requirements."
    })

@app.errorhandler(413)
def file_too_large(_error):
    return jsonify({"error": "That file is too large. Please upload a file smaller than 12 MB."}), 413

if __name__ == "__main__":
    app.run(debug=True)
