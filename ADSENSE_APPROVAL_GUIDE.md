# Google AdSense Approval Audit & Setup Guide (`rozgarnewshub.blogspot.com`)

Yeh guide Google AdSense ki 2026 review policies ke mutabiq **Rozgar News Hub** ko approve karwane ka complete blueprint aur 4 ready-to-paste Blogger Pages deti hai.

---

## 🔍 Part 1: Honest AdSense Readiness Audit Scorecard

| Requirement | Current Theme Status | Tumhe Kya Karna Hai? |
| :--- | :--- | :--- |
| **Footer Legal Navigation** | ✅ **Theme Ready** (`About Us`, `Contact Us`, `Privacy Policy`, `Terms & Disclaimer`, `Sitemap`) | Blogger -> **Pages** me neeche diye 4 pages publish karne hain. |
| **Header Navigation Across Pages** | ✅ **Fixed** (Links now resolve back to homepage sections cleanly + `About` & `Contact`) | Koi extra step nahi. |
| **Cookie / GDPR Notice** | ✅ **Built-in** (`#jm-cookie-bar` disclosing cookies & local storage) | Automatic chalega. |
| **Custom 404 & Clean Static Pages** | ✅ **Fixed** (`data:view.isError` & `data:view.isPage` separated from job posts) | Automatic chalega. |
| **Non-Government & Zero-Fee Disclaimer** | ✅ **Built-in Footer Disclaimer** | Google job-site compliance ke liye zaroori. |
| **Ad Experience During Review** | ⚠️ **Action Needed Before Submitting!** | Monetag + Adsterra Social Bar fake `"$50,000 bonus"` popups AdSense review **fail** karwa dete hain — neeche Step 3 dekho! |
| **Original Content Articles** | ⚠️ **Needs 10–15 Original Posts** | Automated `jobs.json` ke ilawa **10–15 manual original job guides / Pakistan career posts (400+ words each)** publish karo! |

---

## 📄 Part 2: 4 Mandatory Blogger Pages (Copy-Paste Ready!)

Blogger Dashboard -> **Pages** -> **+ New Page** par jao.  
Har page me top-left **Pencil icon (`✏️`) -> HTML view** select karo, Exact Title likho (taake Blogger sahi `/p/...html` URL banaye!), code paste karo, aur **Publish** dabao!

---

### Page 1 — Exact Title: `About Us`
*(Verify permalink ends with `/p/about-us.html`)*

```html
<p>Welcome to <strong>Rozgar News Hub</strong> (<code>rozgarnewshub.blogspot.com</code>), an independent online career portal dedicated to helping students, fresh graduates, and remote professionals in Pakistan discover verified work-from-home and international remote job opportunities.</p>

<h2>Our Mission</h2>
<p>Every day, thousands of job seekers in Pakistan encounter misleading social media job posts requesting upfront registration fees, training charges, or security deposits. <strong>Rozgar News Hub</strong> exists to eliminate fake recruitment traps by combining public job feeds with automated domain trust checks, transparent salary calculators, and Scam-Shield keyword analysis.</p>

<h2>What We Offer</h2>
<ul>
  <li><strong>Scam-Shield Verified Listings:</strong> Automated screening for fee-scam keywords and direct links to official employer portals.</li>
  <li><strong>Remote Salary-to-PKR Estimator:</strong> Transparent currency estimation helping remote candidates understand monthly net take-home compensation.</li>
  <li><strong>ATS Resume &amp; Cover Pitch Helpers:</strong> Free local browser tools to help applicants tailor resumes and cover emails before applying.</li>
  <li><strong>Original Career Guides:</strong> Practical advice for Pakistani students and freelancers entering remote software, customer support, data entry, and content roles.</li>
</ul>

<h2>Editorial Policy</h2>
<p>Rozgar News Hub is an informational directory only. We never charge job seekers any fee to view listings or apply, and we always encourage candidates to verify employer websites directly before sharing personal identity documents.</p>
```

---

### Page 2 — Exact Title: `Contact Us`
*(Verify permalink ends with `/p/contact-us.html` — Note: Apna asli Gmail `YOUR_EMAIL@gmail.com` replace kar lena!)*

```html
<p>Have a question, want to report a suspicious job listing, or need to reach the <strong>Rozgar News Hub</strong> editorial team? Use the contact details or inquiry helper below.</p>

<h2>Official Contact Channels</h2>
<ul>
  <li><strong>Editorial &amp; Scam Reports Email:</strong> <a href="mailto:YOUR_EMAIL@gmail.com">YOUR_EMAIL@gmail.com</a></li>
  <li><strong>Response Time:</strong> Typically within 24–48 business hours.</li>
  <li><strong>Location:</strong> Pakistan (Serving remote and digital career seekers nationwide)</li>
</ul>

<h2>Quick Inquiry Builder</h2>
<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:18px;max-width:560px;margin:16px 0;">
  <label for="jm-c-name" style="display:block;font-weight:600;margin-bottom:4px;">Your Name</label>
  <input id="jm-c-name" type="text" placeholder="Enter your full name" style="width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:8px;margin-bottom:12px;" />

  <label for="jm-c-topic" style="display:block;font-weight:600;margin-bottom:4px;">Topic</label>
  <select id="jm-c-topic" style="width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:8px;margin-bottom:12px;">
    <option value="Report Suspicious Job">Report a Suspicious Job Listing</option>
    <option value="Employer Partnership">Employer / Listing Inquiry</option>
    <option value="Website Feedback">Technical / Website Feedback</option>
    <option value="Privacy Request">Privacy / Data Removal Request</option>
  </select>

  <label for="jm-c-msg" style="display:block;font-weight:600;margin-bottom:4px;">Message</label>
  <textarea id="jm-c-msg" rows="4" placeholder="Write your message or paste the job URL here..." style="width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:8px;margin-bottom:12px;"></textarea>

  <button type="button" onclick="(function(){var n=document.getElementById('jm-c-name').value||'Visitor';var t=document.getElementById('jm-c-topic').value;var m=document.getElementById('jm-c-msg').value||'';window.location.href='mailto:YOUR_EMAIL@gmail.com?subject='+encodeURIComponent('[Rozgar News] '+t+' - '+n)+'&body='+encodeURIComponent(m);})();" style="background:#059669;color:#ffffff;border:none;padding:10px 18px;border-radius:8px;font-weight:700;cursor:pointer;">
    Send Message via Email &#8594;
  </button>
</div>
```

---

### Page 3 — Exact Title: `Privacy Policy`
*(Verify permalink ends with `/p/privacy-policy.html` — Update `YOUR_EMAIL@gmail.com` below!)*

```html
<p><strong>Last Updated:</strong> November 2026</p>

<p>At <strong>Rozgar News Hub</strong> (accessible from <code>https://rozgarnewshub.blogspot.com/</code>), one of our main priorities is the privacy of our visitors. This Privacy Policy explains what types of information are collected and how we use it.</p>

<h2>1. Information We Store Locally</h2>
<p>Our website tools — including <strong>Saved Jobs</strong>, the <strong>ATS Skill Matcher</strong>, and the <strong>Scam-Shield Checker</strong> — run directly inside your web browser using local storage (<code>localStorage</code>). We do not upload your saved skills, CV text, or salary inputs to private servers.</p>

<h2>2. Log Files</h2>
<p>Rozgar News Hub follows a standard procedure of using log files through Google Blogger infrastructure. These files log visitors when they visit websites (IP addresses, browser type, Internet Service Provider, date/time stamp, referring/exit pages). This information is not linked to anything personally identifiable and is used for analyzing trends and site security.</p>

<h2>3. Cookies, Google AdSense &amp; Advertising Partners</h2>
<p>Like most modern websites, Rozgar News Hub uses cookies to store visitor preferences (such as dismissing the cookie notice) and optimize user experience.</p>
<ul>
  <li><strong>Google DoubleClick / AdSense Cookie:</strong> Third-party vendors, including Google, use cookies (such as the DART cookie) to serve ads based on a visitor's prior visits to our website or other websites on the Internet.</li>
  <li>Users may opt out of personalized advertising by visiting <a href="https://adssettings.google.com/" target="_blank" rel="noopener noreferrer">Google Ads Settings</a> or <a href="https://www.aboutads.info/choices/" target="_blank" rel="noopener noreferrer">www.aboutads.info</a>.</li>
  <li>Other advertising partners (such as Adsterra or Monetag, when active) may also use cookies, JavaScript, or web beacons in their respective ad units to measure effectiveness. Rozgar News Hub has no direct access or control over cookies used by third-party advertisers.</li>
</ul>

<h2>4. Third-Party Links</h2>
<p>Job application buttons redirect visitors to external employer websites or public job boards. We strongly advise reviewing the Privacy Policies of those third-party websites, as our policy applies strictly to <code>rozgarnewshub.blogspot.com</code>.</p>

<h2>5. GDPR &amp; User Consent</h2>
<p>Depending on your region, you have the right to disable cookies through your browser settings, request deletion of inquiry emails, or opt out of personalized ads via the links above.</p>

<h2>6. Contact Information</h2>
<p>If you have additional questions about our Privacy Policy, please contact us at <a href="mailto:YOUR_EMAIL@gmail.com">YOUR_EMAIL@gmail.com</a> or visit our <a href="/p/contact-us.html">Contact Us</a> page.</p>
```

---

### Page 4 — Exact Title: `Terms and Disclaimer`
*(Verify permalink automatically becomes `/p/terms-and-disclaimer.html` — in Blogger Pages, publish it with title `Terms and Disclaimer` so the URL slug matches the theme footer link `/p/terms-and-disclaimer.html`!)*

```html
<p><strong>Last Updated:</strong> November 2026</p>

<p>By accessing and using <strong>Rozgar News Hub</strong> (<code>https://rozgarnewshub.blogspot.com/</code>), you agree to the following terms and disclaimers.</p>

<h2>1. Non-Affiliation &amp; Independent Portal Notice</h2>
<p>Rozgar News Hub is an independent informational career directory. We are <strong>not affiliated with any government ministry, public commission, or third-party employer</strong> featured on this site. All company names, trademarks, and brand logos belong to their respective owners.</p>

<h2>2. Zero-Fee Guarantee &amp; Scam Awareness</h2>
<p>Rozgar News Hub <strong>never asks for money, registration fees, Easypaisa/JazzCash deposits, or bank transfers</strong> to apply for any listing. While we screen public job feeds using automated trust checks, employers and external URLs can change over time. Candidates must verify official company domains before sharing CNIC, passport, or financial details.</p>

<h2>3. Accuracy of Salary &amp; Role Information</h2>
<p>The Remote Salary-to-PKR Calculator uses indicative exchange rates for educational estimation only and does not represent guaranteed bank conversion rates or employer offers. Actual compensation, schedules, and eligibility depend solely on the hiring employer.</p>

<h2>4. Limitation of Liability</h2>
<p>Information on Rozgar News Hub is provided in good faith for general informational purposes. We are not liable for hiring outcomes, third-party website availability, or losses arising from external employer interactions.</p>

<h2>5. Intellectual Property &amp; Fair Use</h2>
<p>Original articles, tool utilities, and site design belong to Rozgar News Hub. Job titles and summaries link directly to their official source postings.</p>
```

---

## 🚀 Part 3: Pre-Submit Checklist (AdSense Apply Karne Se Pehle!)

1. **Publish All 4 Pages Above:** Verify every Footer link opens properly without a 404.
2. **Publish 12–15 Original Blogger Posts (Very Important!):**
   - Automated `jobs.json` feed sirf client-side dashboard hai; Google AdSense crawlers original written content bhi dekhte hain.
   - Weekly 3–4 original **400+ word** career guides / Pakistan job roundups publish karo (e.g., *"How Students in Pakistan Can Find Verified Remote Customer Support Jobs in 2026"*, *"Top 7 Zero-Fee Online Typing & Data Entry Platforms"*, *"How to Write an ATS-Friendly CV for Remote Tech Jobs"*).
   - Theme un sab ko automatic **Page 1 ke TOP (`📌 Featured`)** par dikhayega!
3. **AdSense Review Mode Switch (CRITICAL! ⚠️):**
   Jab AdSense me **"Request Review"** click karne lagoge:
   - [blogger-magic-jobs-theme.xml](blogger-magic-jobs-theme.xml) me `CONFIG.adsenseReviewMode` ko `false` se **`true`** kar dena (is se countdown apply modal aur third-party banners review ke dauran band rahenge!).
   - Theme `<head>` se `<script ... quge5.com ...>` (Monetag) aur Blogger **Layout -> Zone 6 (`global_ad_scripts_section`)** se Adsterra Social Bar (`"$50,000 bonus missed call"` widget) **temporarily remove** kar dena jab tak AdSense approve na ho jaye!
   - **Kyun?** AdSense policy popunders aur fake notification banners ke khilaaf strict hai. Approval milne ke baad tumhare paas AdSense khud high-paying safe display ads dega!
4. **Domain Age & Search Console:** Ensure `sitemap.xml` aur `sitemap-pages.xml` Google Search Console me submitted hain taake yeh 4 naye policy pages bhi Google me index hon.
