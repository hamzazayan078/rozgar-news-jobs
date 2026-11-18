# Rozgar News (`rozgarnewshub.blogspot.com`) — Rs. 0 Auto-Updating Blogger Jobs Portal

Is project mein **complete Rs. 0 automation stack** built hai (zero external Python libraries, pure stdlib + Blogger XML):

1. **[blogger-magic-jobs-theme.xml](blogger-magic-jobs-theme.xml)** — Valid Blogger (Blogspot) Landing Page Theme (`Rozgar News` branding, Responsive Job Cards, Live Search, Category Filters, Scam-Shield Checker, ATS Resume Keyword Matcher, 1-Click Cover Email Generator, Day-1 ATS Resume CTA, aur Clean Policy-Safe Ad Slots).
2. **[auto_job_magic.py](auto_job_magic.py)** — Pure Python automation engine jo legal public APIs (**Remotive**, **Arbeitnow**, aur kisi bhi **RSS/Atom** feed) se roz fresh jobs fetch karta hai, HTML sanitize karta hai (XSS-safe), Scam-Shield score + Google `JobPosting` JSON-LD Schema + **1080x1350 SVG Job Posters** (`output/posters/`) generate karta hai, `docs/jobs.json` update karta hai, aur optionally **Gemini AI tips**, **Telegram Channel**, aur **Blogger** par auto-post bhi karta hai.

---

## Step 1: Local Preview Dekho (10 Seconds)

Terminal mein `e:\champion` folder mein run karo:

```powershell
python auto_job_magic.py --demo
python -m http.server 8080 -d docs
```

Phir browser mein `http://localhost:8080` kholo (ya direct `docs/index.html` open karo).

---

## Step 2: Blogger Par Magic Landing Page Lagao

1. Apne **Blogger Dashboard** mein jao -> **Theme** -> **Customize** ke sath wale drop-down arrow par click karo -> **Edit HTML**.
2. Purana saara code select karke delete karo.
3. **[blogger-magic-jobs-theme.xml](blogger-magic-jobs-theme.xml)** ka poora code copy karke paste karo aur **Save** dabao.

### Clean Ads Kaise Lagayein (Ban-Proof Monetization)
Ab theme ke andar **Blogger Layout Gadgets** bhi built-in hain (`header_ad_section` aur `post_footer_ad_section`):
1. Blogger Dashboard → **Layout** par jao.
2. **Header Ad** ya **Post Footer Ad** section mein **Add a Gadget → HTML/JavaScript** choose karo.
3. Apna **Google AdSense**, **Adsterra**, ya clean banner HTML paste kar ke Save dabao (bina XML edit kiye!).
*(Aur In-Feed + Modal slots bhi automatically jobs ke sath render hote hain — pop-unders se bacho taake users aur Google dono khush rahein).*

---

## Step 3: Rs. 0 Daily Auto-Update Activate Karo (GitHub Actions — Bina `git.exe` Ke!)

1. GitHub par ek free repository banao (e.g. `rozgar-news-jobs`) aur aik fine-grained Personal Access Token lo (`Contents: Read and write`).
2. `e:\champion` mein chalao:
   ```powershell
   $env:GITHUB_TOKEN="YOUR_GITHUB_TOKEN"
   python github_sync.py --owner YOUR_USERNAME --repo rozgar-news-jobs
   ```
3. Repo ke **Settings → Actions → General** mein **Workflow permissions = Read and write permissions** ON karo.
4. **[.github/workflows/auto-fetch-jobs.yml](.github/workflows/auto-fetch-jobs.yml)** har 6 ghante baad **Remotive + Arbeitnow + Jobicy + WeWorkRemotely** se real jobs fetch kar ke `docs/jobs.json` update karega!
5. Apne Blogger Theme mein `CONFIG.externalFeedUrl` pehle se hi tere live repo par set hai:
   ```js
   externalFeedUrl: "https://raw.githubusercontent.com/hamzazayan078/rozgar-news-jobs/main/docs/jobs.json",
   ```
   Bas! Ab bina kisi PC ya server ke `rozgarnewshub.blogspot.com` par roz fresh real jobs update hoti rahengi!

### Optional: Individual SEO Blogger Posts Bhi Auto-Upload Karni Hon?
Agar har job ka alag Blogger post bhi auto-publish karna hai (Google Jobs JSON-LD Schema ke sath), toh GitHub **Repository Secrets** mein in mein se koi ek setup add karo:
- **Option A (Mail2Blogger — Sabse Aasaan):** Blogger **Settings -> Email -> Post using email** mein secret email banao, phir GitHub Secrets mein `BLOGGER_SECRET_EMAIL`, `SMTP_USER`, aur Gmail App Password `SMTP_APP_PASS` add kar do.
- **Option B (Official Blogger API v3):** `BLOGGER_BLOG_ID` aur `BLOGGER_OAUTH_TOKEN` add karo.

---

## Step 4: Tests Chalao

```powershell
python -m unittest -v test_auto_job_magic.py
```

