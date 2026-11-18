"""Unit and theme validation tests for Auto Job Magic Engine."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import auto_job_magic as jm
import github_sync as gs


class AutoJobMagicTests(unittest.TestCase):
    """Covers HTML security, feed parsers, Scam-Shield, schema, and Blogger XML."""

    def test_sanitize_html_strips_xss_vectors(self) -> None:
        dirty = (
            '<p onclick="alert(1)">Great role!</p>'
            '<script>alert("xss")</script>'
            '<iframe src="https://evil.example"></iframe>'
            '<a href="javascript:alert(1)">Bad Link</a>'
            '<a href="https://trusted.example/apply">Apply Here</a>'
            "<p>Unclosed paragraph"
        )
        cleaned = jm.sanitize_html(dirty)
        self.assertNotIn("<script", cleaned.lower())
        self.assertNotIn("alert(1)", cleaned)
        self.assertNotIn("<iframe", cleaned.lower())
        self.assertNotIn("javascript:", cleaned.lower())
        self.assertIn('<a href="https://trusted.example/apply"', cleaned)
        self.assertIn('rel="noopener noreferrer"', cleaned)
        self.assertTrue(cleaned.endswith("</p>"))

    def test_scam_shield_detects_fee_scams_and_rewards_clean_posts(self) -> None:
        scam = jm.compute_scam_shield(
            "Easy Data Entry",
            "Unknown",
            "http://unverified.example/apply",
            "Pay a registration fee via easypaisa first.",
        )
        self.assertEqual(scam["level"], "low")
        self.assertLess(scam["score"], 60)

        legit = jm.compute_scam_shield(
            "Backend Python Engineer",
            "Acme Cloud",
            "https://acme.example/careers/python",
            "We build distributed APIs and open-source tools. " * 10,
        )
        self.assertEqual(legit["level"], "high")
        self.assertGreaterEqual(legit["score"], 85)

    def test_parse_remotive_and_arbeitnow_and_rss(self) -> None:
        remotive_sample = {
            "jobs": [
                {
                    "id": 101,
                    "url": "https://remotive.com/remote-jobs/software-dev/python-101",
                    "title": "Python Developer",
                    "company_name": "RemoteCo",
                    "category": "Software Development",
                    "job_type": "full_time",
                    "publication_date": "2026-11-18T10:00:00",
                    "candidate_required_location": "Worldwide",
                    "salary": "$70k",
                    "description": "<p>Build Python APIs and SQL schemas.</p>",
                    "tags": ["Python", "SQL"],
                }
            ]
        }
        rem_jobs = jm.parse_remotive_payload(remotive_sample, limit=5)
        self.assertEqual(len(rem_jobs), 1)
        self.assertEqual(rem_jobs[0]["source"], "Remotive")
        self.assertIn("Python", rem_jobs[0]["ats_keywords"])

        arbeit_sample = {
            "data": [
                {
                    "slug": "support-1",
                    "company_name": "BerlinSaaS",
                    "title": "Technical Support Specialist",
                    "description": "<p>Help customers via email and chat.</p>",
                    "remote": True,
                    "url": "https://www.arbeitnow.com/jobs/support-1",
                    "tags": ["Support", "SaaS"],
                    "job_types": ["Full Time"],
                    "location": "Berlin / Remote",
                    "created_at": 1760000000,
                }
            ]
        }
        arb_jobs = jm.parse_arbeitnow_payload(arbeit_sample, limit=5)
        self.assertEqual(len(arb_jobs), 1)
        self.assertTrue(arb_jobs[0]["remote"])

        jobicy_sample = {
            "jobs": [
                {
                    "id": 202,
                    "url": "https://jobicy.com/jobs/202-qa-remote",
                    "title": "QA Automation Engineer",
                    "companyName": "QualityFlow",
                    "jobIndustry": ["Engineering"],
                    "jobType": ["full-time"],
                    "jobGeo": "Worldwide",
                    "annualSalaryMin": "50000",
                    "annualSalaryMax": "70000",
                    "salaryCurrency": "USD",
                    "pubDate": "2026-11-18T12:00:00",
                    "jobDescription": "<p>Write automated tests in Python.</p>",
                }
            ]
        }
        jobicy_jobs = jm.parse_jobicy_payload(jobicy_sample, limit=5)
        self.assertEqual(len(jobicy_jobs), 1)
        self.assertEqual(jobicy_jobs[0]["source"], "Jobicy")
        self.assertEqual(jobicy_jobs[0]["salary"], "USD 50000-70000/yr")

        rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0"><channel><item>
          <title>Remote Video Editor</title>
          <link>https://jobs.example.com/video-editor</link>
          <description>Edit YouTube Shorts in Premiere Pro.</description>
          <category>Design</category>
        </item></channel></rss>"""
        rss_jobs = jm.parse_rss_or_atom(rss_xml, source_name="DemoRSS", limit=5)
        self.assertEqual(len(rss_jobs), 1)
        self.assertEqual(rss_jobs[0]["title"], "Remote Video Editor")

    def test_jobposting_jsonld_and_post_html(self) -> None:
        sample = jm.get_sample_jobs()[0]
        schema = json.loads(jm.build_jobposting_jsonld(sample))
        self.assertEqual(schema["@type"], "JobPosting")
        self.assertEqual(schema["jobLocationType"], "TELECOMMUTE")

        post_html = jm.render_blogger_post_html(sample)
        self.assertIn("application/ld+json", post_html)
        self.assertIn("Scam-Shield Score", post_html)
        self.assertIn("AD_SLOT_IN_POST", post_html)
        self.assertIn('data-company="', post_html)
        self.assertIn('data-applyurl="', post_html)

        mail_html = jm.render_blogger_post_html(sample, include_jsonld=False)
        self.assertNotIn("<script", mail_html.lower())
        self.assertIn("Scam-Shield Score", mail_html)

    def test_state_deduplication_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "posted_ids.json"
            jm.save_posted_ids(state_path, {"abc123", "xyz789"})
            loaded = jm.load_posted_ids(state_path)
            self.assertEqual(loaded, {"abc123", "xyz789"})

    def test_blogger_xml_theme_is_valid_xml_and_exports_clean_preview(self) -> None:
        root_dir = Path(__file__).resolve().parent
        theme_path = root_dir / "blogger-magic-jobs-theme.xml"
        self.assertTrue(theme_path.exists(), "Blogger XML theme file must exist")

        tree = ET.parse(theme_path)
        xml_root = tree.getroot()
        self.assertTrue(xml_root.tag.endswith("html"))

        raw_xml = theme_path.read_text(encoding="utf-8")
        self.assertIn("<b:skin><![CDATA[", raw_xml)
        self.assertIn("<b:section", raw_xml)
        self.assertIn("id='Blog1'", raw_xml)

        # Verify all 7 Blogger sections exist and have 100% unique IDs (required by Blogger XML parser).
        section_ids = [
            el.attrib.get("id")
            for el in xml_root.iter()
            if el.tag.endswith("section")
        ]
        expected_sections = {
            "header_ad_section",
            "infeed_ad_section",
            "sidebar_ad_section",
            "native_ad_section",
            "main",
            "post_footer_ad_section",
            "global_ad_scripts_section",
        }
        self.assertEqual(len(section_ids), len(set(section_ids)), "Duplicate b:section IDs break Blogger save")
        self.assertTrue(expected_sections.issubset(set(section_ids)))

        # Ensure no b:section is nested inside a b:widget (otherwise Blogger Layout hides it).
        for widget in xml_root.iter():
            if widget.tag.endswith("widget"):
                nested_sections = [el for el in widget.iter() if el.tag.endswith("section")]
                self.assertEqual(nested_sections, [], "b:section must not be nested inside b:widget")

        with tempfile.TemporaryDirectory() as tmp:
            preview_path = Path(tmp) / "index.html"
            jm.export_standalone_preview(theme_path, preview_path)
            preview_html = preview_path.read_text(encoding="utf-8")
            self.assertIn("<!DOCTYPE html>", preview_html)
            self.assertNotIn("<b:", preview_html)
            self.assertNotIn("<data:", preview_html)
            self.assertIn('externalFeedUrl: "./jobs.json"', preview_html)
            self.assertIn("Rozgar News", preview_html)

    def test_poster_svg_and_telegram_message_and_gemini_fallback(self) -> None:
        sample = dict(jm.get_sample_jobs()[0])
        sample["company"] = 'Evil <script>Corp & Co</script>'
        svg_text = jm.generate_job_poster_svg(sample, site_domain="rozgarnewshub.blogspot.com")
        svg_root = ET.fromstring(svg_text)
        self.assertTrue(svg_root.tag.endswith("svg"))
        self.assertIn("rozgarnewshub.blogspot.com", svg_text)
        self.assertNotIn("<script>", svg_text)

        tg_msg = jm.build_telegram_job_message(sample, site_url="https://rozgarnewshub.blogspot.com")
        self.assertIn("https://rozgarnewshub.blogspot.com", tg_msg)
        self.assertIn("Trust Score", tg_msg)

        self.assertEqual(jm.maybe_enrich_with_gemini(sample, ""), "")

    def test_github_sync_payload_builder(self) -> None:
        payload = gs.build_upsert_payload(
            content_bytes=b"hello rozgar",
            message="sync test",
            branch="main",
            existing_sha="deadbeef",
        )
        self.assertEqual(payload["branch"], "main")
        self.assertEqual(payload["sha"], "deadbeef")
        self.assertEqual(payload["content"], "aGVsbG8gcm96Z2Fy")


if __name__ == "__main__":
    unittest.main()

