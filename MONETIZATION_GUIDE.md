# Monetag + Adsterra Dual-Network High-RPM Setup Guide (`rozgarnewshub.blogspot.com`)

Yeh guide tujhe **Adsterra** aur **Monetag** dono ko ek sath **100% clean, non-conflicting, aur high-earning** tareeqe se lagana sikhati hai — taake:
- Har visitor se **multiple viewable impressions** milein (Top + Sticky Sidebar + Mid-Feed + Native + Single Post + Global In-Page Push),
- Aur job seeker ko bhi **real Apply link + ATS keywords + Salary PKR Calculator + Cover Email** bina kisi fake trap ke mile (taake wo roz wapas aaye aur doston ko link share kare!).

---

## Step 1: Blogger Layout Mein 6 Ready Ad Zones (Zero XML Editing!)

Pehle naya upgraded **[blogger-magic-jobs-theme.xml](blogger-magic-jobs-theme.xml)** Blogger par upload kar (`Theme -> ▼ -> Restore -> Upload`).

Uske baad **Blogger Dashboard -> Layout** mein jao — tujhe ye **6 clean zones** milenge. Har zone mein **+ Add a Gadget -> HTML/JavaScript** click karke apna code paste karna hai:

| Zone # | Blogger Layout Section ID | Best Network & Ad Unit | Kyun Best Hai? |
| :--- | :--- | :--- | :--- |
| **Zone 1** | `header_ad_section` | **Adsterra Banner (`728×90` Desktop / `320×50` Mobile)** | Above-the-fold 90%+ viewability — har visitor pehli screen par dekhta hai. |
| **Zone 2** | `infeed_ad_section` | **Monetag Display / Vignette OR Adsterra `468×60`** | Jobs list ke bilkul beech mein natural scroll placement. |
| **Zone 3** | `sidebar_ad_section` | **Adsterra `300×250` + Monetag Banner (Sticky!)** | Desktop par scroll karte waqt chipka rehta hai -> sabse zyada active view-time & CPM! |
| **Zone 4** | `native_ad_section` | **Adsterra Native Banner (`4×1` Grid)** | Job cards jaisa clean look — Adsterra mein sabse zyada legit CTR deta hai! |
| **Zone 5** | `post_footer_ad_section` | **Adsterra Native OR Monetag Banner** | Har individual Google-ranked Blogger job post ke end par extra earning! |
| **Zone 6** | `global_ad_scripts_section` | **Monetag In-Page Push + Adsterra Social Bar** | Alag isolated zone taake dono networks ke async scripts aapas mein clash na karein. |

> **Smart Auto-Hide Feature:** Jaise hi tu kisi zone mein Blogger Layout ka HTML/JavaScript gadget add karega, humara theme khud-ba-khud dashed placeholder text chhupa kar sirf tera live ad dikhayega!

---

## Step 2: Monetag Verification Meta Tag Kahan Lagana Hai?

Monetag site verify karne ke liye ek `<meta name="monetag" content="...">` tag deta hai:
1. Blogger -> **Theme -> Edit HTML** kholo.
2. Line 7 par ye comment milega:
   `<!-- MONETAG / ADSTERRA VERIFICATION META TAG: ... -->`
3. Uske bilkul neeche apna `<meta name='monetag' content='YOUR_CODE'/>` paste karo (**dhyaan rakhna XML ke liye end mein `/>` zaroor lagana!**) aur Save dabao.

---

## Step 3: Pro High-RPM Rules (Jo Earning 3x Karte Hain!)

1. **Dono Popunders Ek Sath MAT Lagana:** Agar Adsterra Popunder aur Monetag OnClick dono ek sath chala diye, toh browser blocker/Google Safe Browsing site flag kar dega aur user 2 second mein bhaag jayega.
   - **Winning Clean Combo:**
     - **Adsterra:** `728×90` Top Banner + `300×250` Sticky Sidebar + `4×1` Native Banner + *Optional* Social Bar (clean non-intrusive skin).
     - **Monetag:** **In-Page Push** + **Vignette Banner (Frequency Cap: max 1 per user per 10–15 minutes)**!
2. **Retention Tools = Zyada Time On Page = High CPM:**
   - Humne site par **Remote Salary-to-PKR Calculator**, **Scam-Shield Checker**, **Saved Jobs (`★`)**, **Pagination**, aur **ATS Keyword Matcher** daal diye hain — log 2–3 minute ruk kar multiple pages dekhenge, jisse CPM naturally upar jata hai!
3. **Day-1 Bonus Income:**
   - Theme ke `CONFIG.cvOrderUrl` mein apna WhatsApp link daal de (`https://wa.me/923XXXXXXXXX?text=Need%20ATS%20CV`) taake sidebar aur job modal ke **"Upgrade My CV Now"** button se direct orders bhi aayein!

