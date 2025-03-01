from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import spacy
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import re

nlp = spacy.load("en_core_web_sm")

app = FastAPI(
    title="Resume Optimizer API",
    description="API for optimizing resumes based on job descriptions",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "Welcome to Resume Optimizer API",
        "endpoints": {
            "docs": "/docs",
            "optimize": "/optimize"
        }
    }


class ResumeInput(BaseModel):
    resume: str
    job_description: str


def extract_sections(text: str) -> Dict[str, str]:
    sections = {
        'education': '',
        'experience': '',
        'skills': ''
    }

    current_section = ''
    for line in text.split('\n'):
        lower_line = line.lower()
        if any(section in lower_line for section in sections.keys()):
            current_section = next(
                s for s in sections.keys() if s in lower_line)
        elif current_section:
            sections[current_section] += line + '\n'
    return sections


def find_skill_levels(text: str) -> List[Dict]:
    patterns = [
        r'(\d+)\+?\s*years?\s+(?:of\s+)?experience\s+(?:in|with)?\s+([^,.]+)',
        r'(expert|intermediate|beginner)\s+(?:in|with)?\s+([^,.]+)'
    ]
    skills = []
    for pattern in patterns:
        matches = re.finditer(pattern, text.lower())
        for match in matches:
            level, skill = match.groups()
            skills.append({"skill": skill.strip(), "level": level})
    return skills


@app.post("/optimize")
def optimize_resume(data: ResumeInput):
    resume_doc = nlp(data.resume)
    job_desc_doc = nlp(data.job_description)

    # Extract sections
    resume_sections = extract_sections(data.resume)
    job_sections = extract_sections(data.job_description)

    # Basic keyword matching
    resume_keywords = {
        token.lemma_ for token in resume_doc if token.is_alpha and not token.is_stop}
    job_desc_keywords = {
        token.lemma_ for token in job_desc_doc if token.is_alpha and not token.is_stop}

    # Phrase matching
    resume_phrases = [chunk.text.lower() for chunk in resume_doc.noun_chunks]
    job_phrases = [chunk.text.lower() for chunk in job_desc_doc.noun_chunks]

    # Calculate scores
    common_keywords = resume_keywords.intersection(job_desc_keywords)
    keyword_match_score = (
        len(common_keywords) / len(job_desc_keywords)) * 100 if job_desc_keywords else 0

    common_phrases = set(resume_phrases).intersection(set(job_phrases))
    phrase_match_score = (len(common_phrases) /
                          len(job_phrases)) * 100 if job_phrases else 0

    # Skill analysis
    resume_skills = find_skill_levels(data.resume)
    job_skills = find_skill_levels(data.job_description)

    # Generate suggestions
    missing_keywords = job_desc_keywords - resume_keywords
    missing_phrases = set(job_phrases) - set(resume_phrases)

    return {
        "match_scores": {
            "keyword_match": round(keyword_match_score, 2),
            "phrase_match": round(phrase_match_score, 2)
        },
        "suggestions": {
            "missing_keywords": list(missing_keywords),
            "missing_phrases": list(missing_phrases),
            "skills_analysis": resume_skills,
            "section_recommendations": {
                section: "Present" if resume_sections[section] else "Missing"
                for section in resume_sections
            }
        }
    }
