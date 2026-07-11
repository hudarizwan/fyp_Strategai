# 🚀 Supabase Setup - Step by Step (Urdu Guide)

## ⚠️ **شروع کرنے سے پہلے**

آپ کو چاہیے:
- ✅ Gmail account
- ✅ Internet connection
- ✅ 10-15 minutes

---

## 📋 **STEP 1: Supabase Account بنائیں**

### 1.1 - Website پر جائیں
1. Browser میں جائیں: **https://supabase.com**
2. اوپر right side میں **"Start your project"** یا **"Sign In"** button پر click کریں

### 1.2 - Sign Up کریں
1. **"Continue with GitHub"** یا **"Continue with Google"** select کریں
2. اپنا Gmail account استعمال کریں
3. Supabase کو access دیں (Allow/Authorize پر click کریں)

✅ **Done!** آپ کا account بن گیا!

---

## 📋 **STEP 2: نیا Project بنائیں**

### 2.1 - Dashboard پر جائیں
- Sign in کرنے کے بعد آپ **Dashboard** پر پہنچ جائیں گے

### 2.2 - New Project بنائیں
1. **"New Project"** button پر click کریں
2. یہ information fill کریں:

```
Name: StrategAI-DB
Database Password: [کوئی strong password بنائیں]
Region: Southeast Asia (Singapore) - Pakistan کے قریب
Pricing Plan: Free
```

3. **"Create new project"** پر click کریں

⏳ **Wait کریں** - 2-3 minutes لگیں گے project setup ہونے میں

---

## 📋 **STEP 3: Database Connection Details لیں**

### 3.1 - Project Settings میں جائیں
1. Left sidebar میں **⚙️ Settings** پر click کریں
2. **Database** option select کریں

### 3.2 - Connection String copy کریں
1. نیچے scroll کریں **"Connection string"** section تک
2. **URI** tab select کریں
3. **Copy** button پر click کریں

یہ کچھ ایسا ہوگا:
```
postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
```

⚠️ **IMPORTANT:** 
- `[YOUR-PASSWORD]` کو اپنے actual password سے replace کریں
- یہ string **save** کر لیں - بعد میں کام آئے گی!

### 3.3 - Project URL اور API Key لیں
1. Settings میں **API** section پر جائیں
2. یہ چیزیں copy کریں:
   - **Project URL** (مثال: `https://abc123xyz.supabase.co`)
   - **anon public** key (لمبی string ہوگی)

✅ **Done!** اب آپ کے پاس سب credentials ہیں!

---

## 📋 **STEP 4: اپنے Project میں Setup کریں**

### 4.1 - .env File بنائیں

1. **VS Code** میں اپنا project کھولیں
2. Root folder میں نئی file بنائیں: **`.env`**
3. یہ content paste کریں:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key_here
SUPABASE_DB_URL=postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres

# ScraperAPI (already have)
SCRAPERAPI_KEY=your_existing_key

# Apify (already have)
APIFY_API_KEY=your_existing_key
```

4. **اپنی actual values** paste کریں:
   - `SUPABASE_URL` → Step 3.3 سے Project URL
   - `SUPABASE_KEY` → Step 3.3 سے anon key
   - `SUPABASE_DB_URL` → Step 3.2 سے Connection String (password کے ساتھ)

5. **Save** کریں (Ctrl+S)

⚠️ **Security Tip:** `.env` file کو **کبھی git** میں commit نہ کریں!

### 4.2 - Dependencies Install کریں

PowerShell میں run کریں:

```powershell
cd C:\Users\USER\StrategaAi
pip install psycopg2-binary python-dotenv
```

✅ **Done!** Dependencies install ہو گئیں!

---

## 📋 **STEP 5: Test کریں**

### 5.1 - Simple Test Run کریں

PowerShell میں:

```powershell
python test_agents_e2e.py
```

### 5.2 - کیا ہوگا؟
1. **Scraper** چلے گا (30-40 seconds)
2. **NLP Agent** data clean کرے گا
3. **Analytics Agent** pricing recommendation دے گا
4. **Supabase** میں tables automatically بن جائیں گی!

### 5.3 - Output دیکھیں

آپ کو یہ نظر آئے گا:
```
[ECDB] Connected to Supabase PostgreSQL
[NLP Agent] Processing: gaming headset (electronics)
[Analytics Agent] Analyzing: gaming headset (electronics)

RECOMMENDATION:
  BUY PRICE:  700 PKR
  SELL PRICE: 1,082 PKR
  MARGIN:     54.6%
  Confidence: 0.60
```

✅ **Success!** System کام کر رہا ہے!

---

## 📋 **STEP 6: Supabase میں Data Check کریں**

### 6.1 - Dashboard پر جائیں
1. Supabase dashboard کھولیں
2. اپنا project select کریں

### 6.2 - Tables دیکھیں
1. Left sidebar میں **Table Editor** پر click کریں
2. آپ کو 3 tables نظر آئیں گی:
   - ✅ **products** - scraped products
   - ✅ **category_patterns** - learned patterns
   - ✅ **recommendations** - pricing decisions

### 6.3 - Data دیکھیں
- کسی بھی table پر click کریں
- آپ کو data rows نظر آئیں گی
- یہ وہی data ہے جو agents نے store کیا!

✅ **Perfect!** سب کچھ کام کر رہا ہے!

---

## 🎯 **اب کیا کریں؟**

### Option 1: مزید Products Test کریں

```python
# test_agents_e2e.py میں product name change کریں
product = "wireless earbuds"  # یا کوئی اور
category = "electronics"
```

### Option 2: مختلف Categories Try کریں

```python
# Fashion
product = "leather jacket"
category = "fashion"

# Home & Kitchen
product = "air fryer"
category = "home_kitchen"
```

### Option 3: API Endpoint بنائیں

اگلے step میں ہم API endpoints بنائیں گے تاکہ:
- Frontend سے call کر سکیں
- Real-time recommendations مل سکیں

---

## ❓ **Common Problems & Solutions**

### Problem 1: "Connection refused"
**Solution:**
- `.env` file check کریں
- Password correct ہے؟
- Internet connection ہے؟

### Problem 2: "Module not found: psycopg2"
**Solution:**
```powershell
pip install psycopg2-binary
```

### Problem 3: Tables نہیں بن رہے
**Solution:**
- Supabase dashboard میں SQL Editor کھولیں
- Tables manually create کر سکتے ہیں (code `ecdb.py` میں ہے)

### Problem 4: "Permission denied"
**Solution:**
- Supabase project settings check کریں
- Database password correct ہے؟

---

## 📞 **Help Needed?**

اگر کوئی problem آئے تو:

1. **Error message** carefully پڑھیں
2. **Supabase dashboard** check کریں
3. **`.env` file** verify کریں
4. **Dependencies** re-install کریں

---

## ✅ **Checklist - Setup Complete?**

- [ ] Supabase account بنا لیا
- [ ] Project create کر لیا
- [ ] Connection string copy کر لیا
- [ ] `.env` file بنا کر credentials paste کر دیے
- [ ] Dependencies install کر لیں (`psycopg2-binary`, `python-dotenv`)
- [ ] `test_agents_e2e.py` successfully run ہو گیا
- [ ] Supabase dashboard میں tables نظر آ رہی ہیں
- [ ] Data store ہو رہا ہے

اگر سب ✅ ہیں تو **Congratulations! 🎉**

آپ کا system **production-ready** ہے!

---

## 🚀 **Next Steps**

1. **Data Collection** - مختلف categories میں products scrape کریں
2. **API Integration** - Endpoints بنائیں
3. **Frontend** - UI بنائیں
4. **FYP Demo** - Presentation تیار کریں

**All the best for your FYP! 💪**
