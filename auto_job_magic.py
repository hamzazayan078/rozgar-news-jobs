"""
Auto Job Magic Engine (Zero-Dependency Python Standard Library)
--------------------------------------------------------------
Fetches jobs from legal public APIs/feeds (Remotive, Arbeitnow, RSS/Atom),
sanitizes external HTML safely, runs Scam-Shield trust analysis, extracts ATS
keywords, generates Google JobPosting JSON-LD schema + ready-to-send cover
email pitches, exports a CORS-ready `docs/jobs.json` feed, and optionally
publishes new jobs to Blogger via Mail2Blogger (SMTP) or Blogger API v3.
"""

from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import smtplib
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any

USER_AGENT = "RozgarNewsBot/1.0 (+https://rozgarnewshub.blogspot.com)"
HTTP_TIMEOUT_SECONDS = 15
DEFAULT_SITE_NAME = "Rozgar News"
DEFAULT_SITE_URL = "https://rozgarnewshub.blogspot.com"

# Tags & attributes considered safe when cleaning external job descriptions.
ALLOWED_HTML_TAGS = {
    "p",
    "br",
    "ul",
    "ol",
    "li",
    "strong",
    "b",
    "em",
    "i",
    "h2",
    "h3",
    "h4",
    "blockquote",
    "code",
    "a",
}
VOID_HTML_TAGS = {"br"}
BLOCKED_CONTENT_TAGS = {"script", "style", "iframe", "object", "embed", "svg", "form"}

# Common tech & professional skills used for fast local ATS keyword extraction.
COMMON_SKILL_KEYWORDS = [
    "python",
    "javascript",
    "typescript",
    "react",
    "node.js",
    "html",
    "css",
    "sql",
    "excel",
    "seo",
    "wordpress",
    "shopify",
    "figma",
    "photoshop",
    "premiere",
    "canva",
    "customer support",
    "sales",
    "marketing",
    "copywriting",
    "data entry",
    "project management",
    "aws",
    "docker",
    "git",
    "api",
    "ui/ux",
    "video editing",
    "virtual assistant",
]

# Phrases commonly associated with fake job scams on social media.
SCAM_RISK_PHRASES = [
    "registration fee",
    "security deposit",
    "processing fee",
    "pay to apply",
    "training fee",
    "send money",
    "easypaisa",
    "jazzcash fee",
    "telegram investment",
    "guaranteed daily income without skills",
]


def is_safe_http_url(url: str | None) -> bool:
    """Allow only absolute http:// or https:// URLs to block javascript:/data: XSS."""
    if not url or not isinstance(url, str):
        return False
    parsed = urllib.parse.urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


class SafeHTMLSanitizer(HTMLParser):
    """Allowlist HTML sanitizer built with stdlib HTMLParser to prevent XSS."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._blocked_depth = 0
        self._open_tag_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in BLOCKED_CONTENT_TAGS:
            self._blocked_depth += 1
            return
        if self._blocked_depth > 0 or tag not in ALLOWED_HTML_TAGS:
            return

        if tag == "a":
            attr_map = {k.lower(): (v or "") for k, v in attrs}
            href = attr_map.get("href", "").strip()
            if is_safe_http_url(href):
                safe_href = html.escape(href, quote=True)
                self._chunks.append(
                    f'<a href="{safe_href}" target="_blank" rel="noopener noreferrer">'
                )
                self._open_tag_stack.append("a")
            return

        self._chunks.append(f"<{tag}>")
        if tag not in VOID_HTML_TAGS:
            self._open_tag_stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in BLOCKED_CONTENT_TAGS:
            if self._blocked_depth > 0:
                self._blocked_depth -= 1
            return
        if self._blocked_depth > 0 or tag not in ALLOWED_HTML_TAGS or tag in VOID_HTML_TAGS:
            return
        if tag in self._open_tag_stack:
            # Close back to matching tag to keep output HTML well-formed.
            while self._open_tag_stack:
                top = self._open_tag_stack.pop()
                self._chunks.append(f"</{top}>")
                if top == tag:
                    break

    def handle_data(self, data: str) -> None:
        if self._blocked_depth == 0:
            self._chunks.append(html.escape(data, quote=False))

    def get_clean_html(self) -> str:
        """Close any dangling tags and return sanitized HTML."""
        while self._open_tag_stack:
            self._chunks.append(f"</{self._open_tag_stack.pop()}>")
        return "".join(self._chunks).strip()


def sanitize_html(raw_html: str) -> str:
    """Sanitize untrusted external HTML using an allowlist parser."""
    if not raw_html:
        return ""
    parser = SafeHTMLSanitizer()
    parser.feed(raw_html)
    parser.close()
    return parser.get_clean_html()


def strip_html_to_text(raw_html: str) -> str:
    """Convert HTML into clean normalized plain text for summaries and scoring."""
    clean = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw_html or "", flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", clean)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def make_job_id(source: str, title: str, company: str, url: str) -> str:
    """Create a stable SHA-256 short identifier for deduplicating jobs across runs."""
    raw = f"{source.strip().lower()}|{title.strip().lower()}|{company.strip().lower()}|{url.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def compute_scam_shield(title: str, company: str, url: str, plain_text: str) -> dict[str, Any]:
    """Evaluate trust signals and return a transparent Scam-Shield breakdown."""
    score = 70
    reasons: list[str] = []
    combined = f"{title} {company} {plain_text}".lower()

    if is_safe_http_url(url) and url.lower().startswith("https://"):
        score += 15
        reasons.append("HTTPS verified source link")
    elif is_safe_http_url(url):
        reasons.append("Non-HTTPS apply link")
    else:
        score -= 40
        reasons.append("Missing valid apply URL")

    if company and company.lower() not in {"confidential", "unknown", "n/a"}:
        score += 10
        reasons.append("Named employer")

    if len(plain_text) >= 180:
        score += 5
        reasons.append("Detailed job description")

    flagged_hits = [phrase for phrase in SCAM_RISK_PHRASES if phrase in combined]
    if flagged_hits:
        score -= 45
        reasons.append(f"Risk phrase detected: {', '.join(flagged_hits[:2])}")

    score = max(0, min(100, score))
    if score >= 85:
        label = "Verified Safe"
        level = "high"
    elif score >= 60:
        label = "Standard Check"
        level = "medium"
    else:
        label = "Caution Advised"
        level = "low"

    return {"score": score, "label": label, "level": level, "reasons": reasons}


def extract_ats_keywords(title: str, tags: list[str], plain_text: str) -> list[str]:
    """Extract clean ATS resume keywords from tags and job description text."""
    seen: set[str] = set()
    keywords: list[str] = []

    for tag in tags:
        cleaned = tag.strip()
        if cleaned and cleaned.lower() not in seen and len(cleaned) <= 28:
            seen.add(cleaned.lower())
            keywords.append(cleaned)

    haystack = f"{title} {plain_text}".lower()
    for skill in COMMON_SKILL_KEYWORDS:
        if skill in haystack and skill not in seen:
            seen.add(skill)
            keywords.append(skill.title() if len(skill) > 3 else skill.upper())

    return keywords[:8]


def generate_cover_pitch(title: str, company: str, keywords: list[str]) -> str:
    """Build a ready-to-send outreach email tailored to the job and ATS skills."""
    top_skills = ", ".join(keywords[:3]) if keywords else "relevant hands-on skills"
    company_name = company or "your team"
    return (
        f"Subject: Application for {title} — Ready to Contribute\n\n"
        f"Hi {company_name} Hiring Team,\n\n"
        f"I noticed your opening for {title} and would love to apply. "
        f"I bring practical experience with {top_skills}, and I focus on delivering "
        f"reliable, measurable results with clear communication.\n\n"
        f"I have attached my resume and relevant work samples for your review. "
        f"Looking forward to a brief conversation.\n\n"
        f"Best regards,\n[Your Name]\n[Your Portfolio / LinkedIn]"
    )


def generate_interview_questions(title: str, category: str, keywords: list[str]) -> list[str]:
    """Create 3 practical interview prep prompts matched to role and keywords."""
    focus = keywords[0] if keywords else (category or "your core domain")
    return [
        f"Walk me through a real project where you applied {focus} for a {title} style problem.",
        "How do you prioritize urgent tasks and communicate blockers when working with a remote or fast-paced team?",
        f"What metric or quality check do you rely on most to verify your work before submitting it?",
    ]


def build_jobposting_jsonld(job: dict[str, Any]) -> str:
    """Generate schema.org JobPosting JSON-LD so Google Search indexes jobs cleanly."""
    payload: dict[str, Any] = {
        "@context": "https://schema.org/",
        "@type": "JobPosting",
        "title": job["title"],
        "description": job["summary"],
        "datePosted": job["published_at"][:10],
        "employmentType": job["job_type"].upper().replace(" ", "_"),
        "hiringOrganization": {
            "@type": "Organization",
            "name": job["company"],
        },
        "jobLocation": {
            "@type": "Place",
            "address": {"@type": "PostalAddress", "addressLocality": job["location"]},
        },
    }
    if job["remote"]:
        payload["jobLocationType"] = "TELECOMMUTE"
    if job["salary"]:
        payload["baseSalary"] = {
            "@type": "MonetaryAmount",
            "value": {"@type": "QuantitativeValue", "value": job["salary"]},
        }
    return json.dumps(payload, ensure_ascii=False)


def normalize_job_record(
    *,
    source: str,
    title: str,
    company: str,
    url: str,
    category: str,
    job_type: str,
    location: str,
    remote: bool,
    salary: str,
    published_at: str,
    raw_description: str,
    tags: list[str] | None = None,
    company_logo: str = "",
) -> dict[str, Any] | None:
    """Validate, sanitize, and enrich a raw job listing into our canonical schema."""
    clean_title = strip_html_to_text(title)
    clean_company = strip_html_to_text(company) or "Verified Employer"
    if not clean_title or not is_safe_http_url(url):
        return None

    clean_html = sanitize_html(raw_description)
    plain_text = strip_html_to_text(clean_html or raw_description)
    summary = (plain_text[:220] + "...") if len(plain_text) > 220 else plain_text
    tag_list = [strip_html_to_text(t) for t in (tags or []) if strip_html_to_text(t)]

    trust = compute_scam_shield(clean_title, clean_company, url, plain_text)
    keywords = extract_ats_keywords(clean_title, tag_list, plain_text)
    pitch = generate_cover_pitch(clean_title, clean_company, keywords)
    questions = generate_interview_questions(clean_title, category, keywords)

    safe_logo = company_logo if is_safe_http_url(company_logo) else ""
    iso_date = published_at or datetime.now(timezone.utc).isoformat()

    record: dict[str, Any] = {
        "id": make_job_id(source, clean_title, clean_company, url),
        "source": source,
        "title": clean_title,
        "company": clean_company,
        "company_logo": safe_logo,
        "url": url.strip(),
        "category": strip_html_to_text(category) or "General",
        "job_type": strip_html_to_text(job_type) or "Full Time",
        "location": strip_html_to_text(location) or ("Remote" if remote else "Global"),
        "remote": bool(remote),
        "salary": strip_html_to_text(salary),
        "published_at": iso_date,
        "summary": summary or f"Apply directly for {clean_title} at {clean_company}.",
        "description_html": clean_html or f"<p>{html.escape(summary)}</p>",
        "tags": tag_list[:6],
        "ats_keywords": keywords,
        "trust": trust,
        "cover_pitch": pitch,
        "interview_questions": questions,
    }
    return record


def http_get_text(url: str, timeout: int = HTTP_TIMEOUT_SECONDS) -> str:
    """Fetch UTF-8 response body using stdlib urllib with explicit timeout."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_remotive_payload(payload: dict[str, Any], limit: int = 15) -> list[dict[str, Any]]:
    """Convert Remotive API JSON payload into canonical job records."""
    results: list[dict[str, Any]] = []
    for item in (payload.get("jobs") or [])[:limit]:
        loc = item.get("candidate_required_location") or "Worldwide"
        job = normalize_job_record(
            source="Remotive",
            title=str(item.get("title", "")),
            company=str(item.get("company_name", "")),
            url=str(item.get("url", "")),
            category=str(item.get("category", "Remote")),
            job_type=str(item.get("job_type", "full_time")).replace("_", " ").title(),
            location=str(loc),
            remote=True,
            salary=str(item.get("salary", "")),
            published_at=str(item.get("publication_date", "")),
            raw_description=str(item.get("description", "")),
            tags=[str(t) for t in (item.get("tags") or [])],
            company_logo=str(item.get("company_logo", "")),
        )
        if job:
            results.append(job)
    return results


def parse_arbeitnow_payload(payload: dict[str, Any], limit: int = 15) -> list[dict[str, Any]]:
    """Convert Arbeitnow Job Board JSON payload into canonical job records."""
    results: list[dict[str, Any]] = []
    for item in (payload.get("data") or [])[:limit]:
        created_ts = item.get("created_at")
        iso_date = (
            datetime.fromtimestamp(int(created_ts), tz=timezone.utc).isoformat()
            if isinstance(created_ts, (int, float))
            else ""
        )
        job_types = item.get("job_types") or ["Full Time"]
        job = normalize_job_record(
            source="Arbeitnow",
            title=str(item.get("title", "")),
            company=str(item.get("company_name", "")),
            url=str(item.get("url", "")),
            category="Tech & Digital",
            job_type=str(job_types[0]) if job_types else "Full Time",
            location=str(item.get("location", "Remote")),
            remote=bool(item.get("remote", False)),
            salary="",
            published_at=iso_date,
            raw_description=str(item.get("description", "")),
            tags=[str(t) for t in (item.get("tags") or [])],
        )
        if job:
            results.append(job)
    return results


def parse_jobicy_payload(payload: dict[str, Any], limit: int = 15) -> list[dict[str, Any]]:
    """Convert Jobicy Remote Jobs API JSON payload into canonical job records."""
    results: list[dict[str, Any]] = []
    for item in (payload.get("jobs") or [])[:limit]:
        industry = item.get("jobIndustry") or ["Remote"]
        jtypes = item.get("jobType") or ["Full Time"]
        sal_min = item.get("annualSalaryMin")
        sal_max = item.get("annualSalaryMax")
        cur = item.get("salaryCurrency") or "USD"
        salary = f"{cur} {sal_min}-{sal_max}/yr" if sal_min and sal_max else ""
        job = normalize_job_record(
            source="Jobicy",
            title=str(item.get("jobTitle") or item.get("title") or ""),
            company=str(item.get("companyName", "")),
            url=str(item.get("url", "")),
            category=str(industry[0]) if isinstance(industry, list) and industry else str(industry),
            job_type=str(jtypes[0]).replace("-", " ").title() if isinstance(jtypes, list) and jtypes else "Full Time",
            location=str(item.get("jobGeo", "Worldwide")),
            remote=True,
            salary=salary,
            published_at=str(item.get("pubDate", "")),
            raw_description=str(item.get("jobDescription") or item.get("jobExcerpt") or ""),
            tags=[str(t) for t in (industry if isinstance(industry, list) else [])],
            company_logo=str(item.get("companyLogo", "")),
        )
        if job:
            results.append(job)
    return results


def parse_rss_or_atom(xml_text: str, source_name: str = "RSS Feed", limit: int = 10) -> list[dict[str, Any]]:
    """Parse standard RSS 2.0 or Atom XML job feeds with stdlib ElementTree."""
    root = ET.fromstring(xml_text)
    results: list[dict[str, Any]] = []

    # RSS 2.0 (<channel><item>...)
    rss_items = root.findall(".//item")
    for item in rss_items[:limit]:
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        desc = item.findtext("description") or ""
        pub = item.findtext("pubDate") or ""
        cats = [c.text for c in item.findall("category") if c.text]
        job = normalize_job_record(
            source=source_name,
            title=title,
            company=source_name,
            url=link,
            category=cats[0] if cats else "General",
            job_type="Full Time",
            location="Remote / Global",
            remote="remote" in f"{title} {desc}".lower(),
            salary="",
            published_at=pub,
            raw_description=desc,
            tags=cats,
        )
        if job:
            results.append(job)

    if results:
        return results

    # Atom (<feed><entry>...)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    atom_entries = root.findall(".//atom:entry", ns) or root.findall(".//entry")
    for entry in atom_entries[:limit]:
        title = entry.findtext("atom:title", default="", namespaces=ns) or entry.findtext("title") or ""
        link_el = entry.find("atom:link", ns) or entry.find("link")
        link = link_el.attrib.get("href", "") if link_el is not None else ""
        summary = (
            entry.findtext("atom:content", default="", namespaces=ns)
            or entry.findtext("atom:summary", default="", namespaces=ns)
            or entry.findtext("summary")
            or ""
        )
        updated = entry.findtext("atom:updated", default="", namespaces=ns) or ""
        job = normalize_job_record(
            source=source_name,
            title=title,
            company=source_name,
            url=link,
            category="General",
            job_type="Full Time",
            location="Remote / Global",
            remote="remote" in f"{title} {summary}".lower(),
            salary="",
            published_at=updated,
            raw_description=summary,
        )
        if job:
            results.append(job)
    return results


def get_sample_jobs() -> list[dict[str, Any]]:
    """Built-in clean sample jobs for offline testing and instant previewing."""
    now_iso = datetime.now(timezone.utc).isoformat()
    raw_samples = [
        {
            "source": "SampleFeed",
            "title": "Junior Python Automation Developer (Remote)",
            "company": "CloudScale Labs",
            "url": "https://remotive.com/remote-jobs/software-dev",
            "category": "Software Development",
            "job_type": "Full Time",
            "location": "Worldwide (Remote)",
            "remote": True,
            "salary": "$1,200 - $1,800/mo",
            "published_at": now_iso,
            "raw_description": (
                "<p>We are hiring a <strong>Junior Python Developer</strong> to build clean API "
                "integrations and JSON data pipelines.</p><ul><li>Python 3 &amp; REST APIs</li>"
                "<li>Git &amp; basic SQL</li><li>Async remote communication</li></ul>"
            ),
            "tags": ["Python", "API", "SQL", "Remote"],
        },
        {
            "source": "SampleFeed",
            "title": "Customer Support Specialist (English Chat & Email)",
            "company": "HelpDesk Pro",
            "url": "https://remotive.com/remote-jobs/customer-support",
            "category": "Customer Support",
            "job_type": "Full Time",
            "location": "Remote - Asia / Europe",
            "remote": True,
            "salary": "$900 - $1,300/mo",
            "published_at": now_iso,
            "raw_description": (
                "<p>Join our friendly remote support team assisting SaaS users over email and live chat.</p>"
                "<ul><li>Clear written English</li><li>Experience with CRM or helpdesk tools</li></ul>"
            ),
            "tags": ["Customer Support", "SaaS", "Remote"],
        },
        {
            "source": "SampleFeed",
            "title": "SEO Content Writer & WordPress Assistant",
            "company": "RankBoost Media",
            "url": "https://remotive.com/remote-jobs/writing",
            "category": "Marketing & SEO",
            "job_type": "Contract",
            "location": "Worldwide (Remote)",
            "remote": True,
            "salary": "$700 - $1,100/mo",
            "published_at": now_iso,
            "raw_description": (
                "<p>Looking for a detail-oriented SEO writer to draft clean tutorials and manage "
                "WordPress formatting.</p><ul><li>Keyword research</li><li>HTML basics &amp; Canva</li></ul>"
            ),
            "tags": ["SEO", "WordPress", "Copywriting", "Canva"],
        },
        {
            "source": "SampleFeed",
            "title": "UI/UX & Social Media Graphic Designer",
            "company": "PixelCraft Studio",
            "url": "https://remotive.com/remote-jobs/design",
            "category": "Design",
            "job_type": "Part Time",
            "location": "Remote",
            "remote": True,
            "salary": "$800 - $1,400/mo",
            "published_at": now_iso,
            "raw_description": (
                "<p>Create crisp landing page concepts in Figma and high-engagement social graphics.</p>"
                "<ul><li>Figma &amp; Photoshop</li><li>Clean typography sense</li></ul>"
            ),
            "tags": ["Figma", "UI/UX", "Photoshop", "Canva"],
        },
        {
            "source": "SampleFeed",
            "title": "Short-Form Video Editor (Reels & YouTube Shorts)",
            "company": "CreatorPulse Media",
            "url": "https://remotive.com/remote-jobs/design",
            "category": "Design",
            "job_type": "Contract",
            "location": "Worldwide (Remote)",
            "remote": True,
            "salary": "$750 - $1,250/mo",
            "published_at": now_iso,
            "raw_description": (
                "<p>Edit high-retention vertical videos with clean captions, pacing, and sound effects.</p>"
                "<ul><li>Premiere Pro / CapCut Desktop</li><li>Clean subtitles &amp; audio mixing</li></ul>"
            ),
            "tags": ["Video Editing", "Premiere", "Canva"],
        },
        {
            "source": "SampleFeed",
            "title": "Remote Virtual Assistant & E-Commerce Operations",
            "company": "NorthStar Commerce",
            "url": "https://remotive.com/remote-jobs/all-others",
            "category": "Operations & VA",
            "job_type": "Full Time",
            "location": "Asia / Europe (Remote)",
            "remote": True,
            "salary": "$650 - $1,000/mo",
            "published_at": now_iso,
            "raw_description": (
                "<p>Support our online storefront operations remotely with clean daily reporting.</p>"
                "<ul><li>Shopify &amp; Excel / Google Sheets</li><li>Order tracking &amp; customer emails</li></ul>"
            ),
            "tags": ["Virtual Assistant", "Shopify", "Excel", "Data Entry"],
        },
    ]
    return [job for s in raw_samples if (job := normalize_job_record(**s)) is not None]


def render_blogger_post_html(job: dict[str, Any], *, include_jsonld: bool = True) -> str:
    """Build clean, SEO-ready HTML (+ optional JSON-LD) for a Blogger post."""
    json_ld_block = (
        f'<script type="application/ld+json">{build_jobposting_jsonld(job)}</script>\n'
        if include_jsonld
        else ""
    )
    esc = html.escape
    kw_badges = "".join(
        f'<span style="display:inline-block;background:#eef2ff;color:#1e3a8a;'
        f'padding:4px 10px;border-radius:999px;font-size:12px;margin:3px;">{esc(k)}</span>'
        for k in job["ats_keywords"]
    )
    questions_li = "".join(f"<li>{esc(q)}</li>" for q in job["interview_questions"])
    trust = job["trust"]
    kw_csv = ", ".join(job["ats_keywords"])

    return f"""{json_ld_block}<div class="jm-post-wrapper"
     data-company="{esc(job["company"], quote=True)}"
     data-location="{esc(job["location"], quote=True)}"
     data-jobtype="{esc(job["job_type"], quote=True)}"
     data-salary="{esc(job["salary"], quote=True)}"
     data-remote="{str(job["remote"]).lower()}"
     data-applyurl="{esc(job["url"], quote=True)}"
     data-trustscore="{trust["score"]}"
     data-trustlabel="{esc(trust["label"], quote=True)}"
     data-keywords="{esc(kw_csv, quote=True)}"
     style="font-family:system-ui,-apple-system,sans-serif;line-height:1.65;color:#0f172a;">
  <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin-bottom:18px;">
    <p style="margin:0 0 6px 0;font-size:13px;color:#475569;">
      <strong>Company:</strong> {esc(job["company"])} &bull;
      <strong>Location:</strong> {esc(job["location"])} &bull;
      <strong>Type:</strong> {esc(job["job_type"])}
    </p>
    <p style="margin:0;font-size:13px;">
      <strong>Scam-Shield Score:</strong> {trust["score"]}/100 ({esc(trust["label"])})
      {f' &bull; <strong>Salary:</strong> {esc(job["salary"])}' if job["salary"] else ""}
    </p>
  </div>

  <!-- AD_SLOT_IN_POST: Replace this clean placeholder with your AdSense unit inside Blogger if desired -->
  <div class="jm-ad-slot" style="border:1px dashed #cbd5e1;border-radius:10px;padding:12px;text-align:center;margin:16px 0;font-size:12px;color:#64748b;">
    Advertisement Space (Clean Responsive Banner)
  </div>

  <h3>Job Overview &amp; Requirements</h3>
  <div class="jm-job-description">
    {job["description_html"]}
  </div>

  <h3>ATS Resume Keywords to Include</h3>
  <div style="margin-bottom:16px;">{kw_badges or "<span>Tailor skills to the role description above.</span>"}</div>

  <h3>Top 3 Interview Prep Prompts</h3>
  <ol>{questions_li}</ol>

  <h3>1-Click Cover Email Template</h3>
  <pre style="background:#0f172a;color:#e2e8f0;padding:14px;border-radius:10px;overflow-x:auto;font-size:13px;white-space:pre-wrap;">{esc(job["cover_pitch"])}</pre>

  <div style="margin-top:22px;text-align:center;">
    <a href="{esc(job["url"], quote=True)}" target="_blank" rel="noopener noreferrer"
       style="display:inline-block;background:#059669;color:#ffffff;padding:14px 28px;border-radius:10px;text-decoration:none;font-weight:700;">
      Apply Officially at {esc(job["company"])} &rarr;
    </a>
    <p style="font-size:12px;color:#64748b;margin-top:8px;">
      Safety tip: Never pay any registration or training fee to apply for a job.
    </p>
  </div>
</div>"""


def fetch_all_sources(
    *,
    limit_per_source: int = 12,
    extra_rss_urls: list[str] | None = None,
    use_demo: bool = False,
    allow_sample_fallback: bool = True,
) -> list[dict[str, Any]]:
    """Fetch jobs across Remotive, Arbeitnow, and custom RSS feeds with safe fallback."""
    if use_demo:
        return get_sample_jobs()

    collected: list[dict[str, Any]] = []
    sources: list[tuple[str, str, Any]] = [
        ("Remotive", f"https://remotive.com/api/remote-jobs?limit={limit_per_source}", parse_remotive_payload),
        ("Arbeitnow", "https://www.arbeitnow.com/api/job-board-api", parse_arbeitnow_payload),
        ("Jobicy", f"https://jobicy.com/api/v2/remote-jobs?count={limit_per_source}", parse_jobicy_payload),
    ]

    for name, url, parser_fn in sources:
        try:
            body = http_get_text(url)
            payload = json.loads(body)
            jobs = parser_fn(payload, limit=limit_per_source)
            print(f"[OK] {name}: fetched {len(jobs)} jobs")
            collected.extend(jobs)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            print(f"[WARN] {name} fetch skipped: {exc}")

    rss_sources = [("WeWorkRemotely", "https://weworkremotely.com/remote-jobs.rss")] + [
        (f"RSS-{idx}", url) for idx, url in enumerate(extra_rss_urls or [], start=1)
    ]
    for source_name, rss_url in rss_sources:
        if not is_safe_http_url(rss_url):
            continue
        try:
            xml_text = http_get_text(rss_url)
            rss_jobs = parse_rss_or_atom(xml_text, source_name=source_name, limit=limit_per_source)
            print(f"[OK] {source_name}: fetched {len(rss_jobs)} jobs")
            collected.extend(rss_jobs)
        except (urllib.error.URLError, ET.ParseError, TimeoutError, OSError) as exc:
            print(f"[WARN] {source_name} skipped: {exc}")

    if not collected and allow_sample_fallback:
        print("[INFO] Using built-in sample jobs because live endpoints were unreachable.")
        return get_sample_jobs()

    return deduplicate_jobs(collected)


def deduplicate_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep unique jobs preserving order."""
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for job in jobs:
        jid = job["id"]
        if jid not in seen:
            seen.add(jid)
            unique.append(job)
    return unique


def load_posted_ids(state_path: Path) -> set[str]:
    """Load previously uploaded job IDs from JSON state file."""
    if not state_path.exists():
        return set()
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        return set(data.get("posted_ids", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_posted_ids(state_path: Path, posted_ids: set[str]) -> None:
    """Persist posted job IDs cleanly so future runs skip duplicates."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "posted_ids": sorted(posted_ids),
    }
    state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def post_via_blogger_api(
    *,
    blog_id: str,
    oauth_token: str,
    title: str,
    html_content: str,
    labels: list[str],
    is_draft: bool = False,
) -> dict[str, Any]:
    """Publish a single job post using the official Blogger API v3."""
    endpoint = f"https://www.googleapis.com/blogger/v3/blogs/{urllib.parse.quote(blog_id)}/posts"
    if is_draft:
        endpoint += "?isDraft=true"
    payload = {
        "kind": "blogger#post",
        "blog": {"id": blog_id},
        "title": title,
        "content": html_content,
        "labels": labels[:5],
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {oauth_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_via_mail2blogger(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
    blogger_secret_email: str,
    title: str,
    html_content: str,
) -> None:
    """Publish a job post via Blogger's built-in Mail2Blogger email endpoint."""
    msg = EmailMessage()
    msg["From"] = smtp_user
    msg["To"] = blogger_secret_email
    msg["Subject"] = title
    msg.set_content(strip_html_to_text(html_content))
    msg.add_alternative(html_content, subtype="html")

    with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=HTTP_TIMEOUT_SECONDS) as server:
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


def maybe_enrich_with_gemini(job: dict[str, Any], api_key: str) -> str:
    """Optionally generate a concise career takeaway via Gemini Free API (falls back safely)."""
    if not api_key:
        return ""
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={urllib.parse.quote(api_key)}"
    )
    prompt = (
        f"Give one short, practical 2-sentence application tip in simple English for a candidate "
        f"applying to '{job['title']}' at '{job['company']}' requiring {', '.join(job['ats_keywords'][:4])}."
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        candidates = data.get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        tip = strip_html_to_text(str(parts[0].get("text", ""))) if parts else ""
        return tip[:320]
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, IndexError, KeyError, OSError):
        return ""


def generate_job_poster_svg(
    job: dict[str, Any],
    *,
    site_domain: str = "rozgarnewshub.blogspot.com",
) -> str:
    """Create a crisp 1080x1350 social media SVG job poster card using stdlib only."""
    esc = html.escape
    title_lines = textwrap.wrap(job["title"], width=26)[:3] or ["Open Position"]
    title_tspans = "".join(
        f'<tspan x="80" dy="{0 if idx == 0 else 66}">{esc(line)}</tspan>'
        for idx, line in enumerate(title_lines)
    )
    skills = job.get("ats_keywords") or [job.get("category", "Remote")]
    skill_pills = "".join(
        f'<g transform="translate({80 + (idx * 290)}, 835)">'
        f'<rect width="270" height="58" rx="29" fill="#1e293b" stroke="#334155" stroke-width="2"/>'
        f'<text x="135" y="38" text-anchor="middle" fill="#e2e8f0" font-family="Arial,sans-serif" font-size="24" font-weight="700">{esc(sk[:15])}</text>'
        f"</g>"
        for idx, sk in enumerate(skills[:3])
    )
    salary_text = job["salary"] if job.get("salary") else f"{job['job_type']} • {job['location']}"
    trust = job["trust"]

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#070b14"/>
      <stop offset="100%" stop-color="#111c36"/>
    </linearGradient>
  </defs>
  <rect width="1080" height="1350" fill="url(#bg)"/>
  <rect x="64" y="64" width="952" height="1222" rx="36" fill="#0f172a" stroke="#1e293b" stroke-width="3"/>

  <rect x="80" y="110" width="420" height="56" rx="28" fill="#064e3b" stroke="#10b981" stroke-width="2"/>
  <text x="290" y="147" text-anchor="middle" fill="#6ee7b7" font-family="Arial,sans-serif" font-size="24" font-weight="700">
    WE ARE HIRING &#8226; VERIFIED {trust['score']}%
  </text>

  <text x="80" y="250" fill="#60a5fa" font-family="Arial,sans-serif" font-size="34" font-weight="700">
    {esc(job['company'][:36])}
  </text>

  <text x="80" y="340" fill="#ffffff" font-family="Arial,sans-serif" font-size="54" font-weight="800">
    {title_tspans}
  </text>

  <rect x="80" y="590" width="920" height="170" rx="22" fill="#172554" opacity="0.55"/>
  <text x="115" y="655" fill="#93c5fd" font-family="Arial,sans-serif" font-size="26" font-weight="700">LOCATION &amp; TYPE</text>
  <text x="115" y="705" fill="#f8fafc" font-family="Arial,sans-serif" font-size="32" font-weight="700">
    {esc((job['location'] + ' • ' + job['job_type'])[:44])}
  </text>
  <text x="115" y="744" fill="#34d399" font-family="Arial,sans-serif" font-size="24" font-weight="700">
    {esc(salary_text[:48])}
  </text>

  <text x="80" y="805" fill="#94a3b8" font-family="Arial,sans-serif" font-size="24" font-weight="700">TOP SKILLS NEEDED</text>
  {skill_pills}

  <rect x="80" y="960" width="920" height="190" rx="26" fill="#059669"/>
  <text x="540" y="1038" text-anchor="middle" fill="#ffffff" font-family="Arial,sans-serif" font-size="38" font-weight="800">
    Apply Link + Cover Email Ready!
  </text>
  <text x="540" y="1098" text-anchor="middle" fill="#ecfdf5" font-family="Arial,sans-serif" font-size="32" font-weight="700">
    Visit: {esc(site_domain)}
  </text>

  <text x="540" y="1230" text-anchor="middle" fill="#64748b" font-family="Arial,sans-serif" font-size="22">
    Scam-Shield Checked &#8226; Never Pay Registration Fees
  </text>
</svg>
"""


def build_telegram_job_message(job: dict[str, Any], site_url: str = DEFAULT_SITE_URL) -> str:
    """Format a clean Telegram channel post linking back to the user's job portal."""
    salary_line = f"Salary: {job['salary']}\n" if job.get("salary") else ""
    skills = ", ".join(job.get("ats_keywords", [])[:4]) or job.get("category", "General")
    return (
        f"NEW VERIFIED JOB ({job['trust']['score']}/100 Trust Score)\n\n"
        f"Role: {job['title']}\n"
        f"Company: {job['company']}\n"
        f"Location: {job['location']} ({job['job_type']})\n"
        f"{salary_line}"
        f"Skills: {skills}\n\n"
        f"Apply Link + Ready Cover Email:\n{site_url}"
    )


def post_to_telegram_if_configured(
    jobs: list[dict[str, Any]],
    *,
    state_path: Path,
    site_url: str = DEFAULT_SITE_URL,
    max_posts: int = 3,
) -> int:
    """Optionally broadcast unseen verified jobs to a Telegram Channel via Bot API."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not (bot_token and chat_id):
        return 0

    posted_ids = load_posted_ids(state_path)
    endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    sent = 0

    for job in jobs:
        if sent >= max_posts:
            break
        if job["id"] in posted_ids or job["trust"]["score"] < 70:
            continue
        payload = {
            "chat_id": chat_id,
            "text": build_telegram_job_message(job, site_url=site_url),
            "disable_web_page_preview": False,
        }
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS):
                posted_ids.add(job["id"])
                sent += 1
                print(f"[TELEGRAM SENT] {job['title']}")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f"[WARN] Telegram send skipped: {exc}")

    if sent > 0:
        save_posted_ids(state_path, posted_ids)
    return sent


def write_feed_and_posts(
    jobs: list[dict[str, Any]],
    *,
    feed_path: Path,
    posts_dir: Path,
    posters_dir: Path | None = None,
    site_domain: str = "rozgarnewshub.blogspot.com",
    max_feed_items: int = 50,
) -> None:
    """Write `docs/jobs.json`, Blogger HTML previews, and SVG social posters."""
    feed_path.parent.mkdir(parents=True, exist_ok=True)
    posts_dir.mkdir(parents=True, exist_ok=True)
    if posters_dir:
        posters_dir.mkdir(parents=True, exist_ok=True)

    feed_payload = {
        "site_name": DEFAULT_SITE_NAME,
        "site_url": DEFAULT_SITE_URL,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_jobs": len(jobs[:max_feed_items]),
        "jobs": jobs[:max_feed_items],
    }
    feed_path.write_text(json.dumps(feed_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    for job in jobs[:10]:
        post_file = posts_dir / f"{job['id']}.html"
        post_file.write_text(render_blogger_post_html(job), encoding="utf-8")
        if posters_dir:
            poster_file = posters_dir / f"{job['id']}.svg"
            poster_file.write_text(
                generate_job_poster_svg(job, site_domain=site_domain),
                encoding="utf-8",
            )


def publish_new_jobs_if_configured(
    jobs: list[dict[str, Any]],
    *,
    state_path: Path,
    max_posts_per_run: int = 3,
    is_draft: bool = False,
) -> int:
    """Publish up to N unseen jobs if Blogger API or Mail2Blogger env vars exist."""
    blog_id = os.environ.get("BLOGGER_BLOG_ID", "").strip()
    oauth_token = os.environ.get("BLOGGER_OAUTH_TOKEN", "").strip()
    secret_email = os.environ.get("BLOGGER_SECRET_EMAIL", "").strip()
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_pass = os.environ.get("SMTP_APP_PASS", "").strip()
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))

    use_api = bool(blog_id and oauth_token)
    use_mail = bool(secret_email and smtp_user and smtp_pass)
    if not (use_api or use_mail):
        print("[INFO] No Blogger upload credentials set; updated docs/jobs.json feed only.")
        return 0

    posted_ids = load_posted_ids(state_path)
    new_jobs = [j for j in jobs if j["id"] not in posted_ids and j["trust"]["score"] >= 60]
    published_count = 0

    for job in new_jobs[:max_posts_per_run]:
        post_title = f"{job['title']} at {job['company']} ({job['location']})"
        try:
            if use_api:
                post_html = render_blogger_post_html(job, include_jsonld=True)
                resp = post_via_blogger_api(
                    blog_id=blog_id,
                    oauth_token=oauth_token,
                    title=post_title,
                    html_content=post_html,
                    labels=[job["category"], "Remote" if job["remote"] else "Onsite", job["job_type"]],
                    is_draft=is_draft,
                )
                print(f"[PUBLISHED API] {post_title} -> {resp.get('url', 'draft')}")
            elif use_mail:
                # Omit <script> tag in email HTML so Mail2Blogger spam filters accept posts cleanly.
                mail_html = render_blogger_post_html(job, include_jsonld=False)
                post_via_mail2blogger(
                    smtp_host=smtp_host,
                    smtp_port=smtp_port,
                    smtp_user=smtp_user,
                    smtp_pass=smtp_pass,
                    blogger_secret_email=secret_email,
                    title=post_title,
                    html_content=mail_html,
                )
                print(f"[PUBLISHED EMAIL] {post_title}")
            posted_ids.add(job["id"])
            published_count += 1
        except (urllib.error.URLError, smtplib.SMTPException, OSError) as exc:
            print(f"[WARN] Failed publishing '{post_title}': {exc}")

    if published_count > 0:
        save_posted_ids(state_path, posted_ids)
    return published_count


def export_standalone_preview(theme_xml_path: Path, output_html_path: Path) -> None:
    """Convert the Blogger XML theme into a clean standalone HTML5 preview/GitHub Pages page."""
    raw = theme_xml_path.read_text(encoding="utf-8")

    # Strip XML header and replace Blogger root attributes with standard HTML5.
    html_out = re.sub(r"<\?xml[^?]*\?>\s*", "", raw, count=1)
    html_out = re.sub(r"<html\b[^>]*>", '<html lang="en">', html_out, count=1)
    html_out = re.sub(
        r"<title>.*?</title>",
        f"<title>{html.escape(DEFAULT_SITE_NAME)} - Verified Daily Jobs &amp; Career Hub</title>",
        html_out,
        count=1,
        flags=re.S,
    )
    html_out = html_out.replace("<b:include data='blog' name='all-head-content'/>", "")
    html_out = html_out.replace("<b:skin><![CDATA[", "<style>").replace("]]></b:skin>", "</style>")
    html_out = html_out.replace("<data:blog.title/>", html.escape(DEFAULT_SITE_NAME))
    html_out = html_out.replace("expr:href='data:blog.homepageUrl'", "href='#'")

    # Remove Blogger conditional wrappers around homepage and strip the Blogger-only Blog1 section.
    html_out = html_out.replace("<b:if cond='data:view.isHomepage'>", "")
    html_out = re.sub(
        r"<!-- Required Blogger Section & Blog1 Widget.*?<!-- Job Detail Modal",
        "<!-- Job Detail Modal",
        html_out,
        count=1,
        flags=re.S,
    )
    # Remove the closing </b:if> left right before the Blog1 section marker and strip standalone ad b:section tags.
    html_out = html_out.replace("</b:if>\n\n  <!-- Job Detail Modal", "<!-- Job Detail Modal")
    html_out = re.sub(r"<b:section\b[^>]*/>", "", html_out)
    html_out = html_out.replace("//<![CDATA[", "").replace("//]]>", "")
    html_out = re.sub(
        r'externalFeedUrl:\s*"[^"]*"',
        'externalFeedUrl: "./jobs.json"',
        html_out,
        count=1,
    )

    output_html_path.parent.mkdir(parents=True, exist_ok=True)
    output_html_path.write_text(html_out.strip() + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for fetching, enriching, exporting, and optionally posting jobs."""
    parser = argparse.ArgumentParser(description="Auto Job Magic Fetcher & Blogger Publisher")
    parser.add_argument("--demo", action="store_true", help="Use built-in sample jobs without network calls")
    parser.add_argument("--limit", type=int, default=12, help="Max jobs per source")
    parser.add_argument("--max-posts", type=int, default=3, help="Max Blogger posts per run")
    parser.add_argument("--draft", action="store_true", help="Publish API posts as drafts")
    parser.add_argument("--rss", action="append", default=[], help="Extra public RSS/Atom job feed URL")
    args = parser.parse_args(argv)

    env_rss = [u.strip() for u in os.environ.get("EXTRA_RSS_FEEDS", "").split(",") if u.strip()]
    site_url = os.environ.get("SITE_URL", DEFAULT_SITE_URL).strip() or DEFAULT_SITE_URL
    site_domain = urllib.parse.urlparse(site_url).netloc or "rozgarnewshub.blogspot.com"
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()

    root_dir = Path(__file__).resolve().parent
    feed_path = root_dir / "docs" / "jobs.json"
    posts_dir = root_dir / "output" / "posts"
    posters_dir = root_dir / "output" / "posters"
    state_path = root_dir / "state" / "posted_ids.json"
    tg_state_path = root_dir / "state" / "telegram_posted_ids.json"
    theme_xml_path = root_dir / "blogger-magic-jobs-theme.xml"
    preview_html_path = root_dir / "docs" / "index.html"

    jobs = fetch_all_sources(
        limit_per_source=args.limit,
        extra_rss_urls=[*args.rss, *env_rss],
        use_demo=args.demo,
        allow_sample_fallback=True,
    )
    if gemini_key:
        for job in jobs[:args.max_posts]:
            tip = maybe_enrich_with_gemini(job, gemini_key)
            if tip:
                job["ai_takeaway"] = tip

    write_feed_and_posts(
        jobs,
        feed_path=feed_path,
        posts_dir=posts_dir,
        posters_dir=posters_dir,
        site_domain=site_domain,
    )
    if theme_xml_path.exists():
        export_standalone_preview(theme_xml_path, preview_html_path)
    print(f"[DONE] Saved {len(jobs)} enriched jobs to {feed_path} and posters to {posters_dir}")

    publish_new_jobs_if_configured(
        jobs,
        state_path=state_path,
        max_posts_per_run=args.max_posts,
        is_draft=args.draft,
    )
    post_to_telegram_if_configured(
        jobs,
        state_path=tg_state_path,
        site_url=site_url,
        max_posts=args.max_posts,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
