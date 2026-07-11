# 🎯 Quick Setup Checklist

## ✅ **5 Minute Setup**

### 1️⃣ Supabase Account (2 min)
```
→ supabase.com پر جائیں
→ Gmail سے sign up کریں
→ New Project بنائیں
   Name: StrategAI-DB
   Password: [strong password]
   Region: Singapore
```

### 2️⃣ Credentials Copy کریں (1 min)
```
Settings → Database → Connection String (URI)
Settings → API → Project URL + anon key
```

### 3️⃣ .env File بنائیں (1 min)
```powershell
# Root folder میں .env file بنائیں
# Paste کریں:

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_DB_URL=postgresql://postgres:password@...
```

### 4️⃣ Dependencies Install (1 min)
```powershell
pip install psycopg2-binary python-dotenv
```

### 5️⃣ Test Run (30 sec)
```powershell
python test_agents_e2e.py
```

---

## 🎯 **کیا Expect کریں؟**

### Test Run کے دوران:
```
[ECDB] Connected to Supabase PostgreSQL ✅
[NLP Agent] Processing: gaming headset
[Analytics Agent] Analyzing...

RECOMMENDATION:
  BUY:  700 PKR
  SELL: 1,082 PKR
  MARGIN: 54.6%
```

### Supabase Dashboard میں:
```
Table Editor → 3 tables:
  ✅ products (11 rows)
  ✅ category_patterns (0 rows - first run)
  ✅ recommendations (1 row)
```

---

## ⚠️ **Common Mistakes**

### ❌ Password غلط
```
Error: connection refused
Fix: .env میں password check کریں
```

### ❌ Dependencies missing
```
Error: No module named 'psycopg2'
Fix: pip install psycopg2-binary
```

### ❌ .env file نہیں بنائی
```
Error: SUPABASE_DB_URL not found
Fix: .env file root folder میں بنائیں
```

---

## 📞 **Help**

اگر stuck ہو جائیں:
1. Error message screenshot لیں
2. `.env` file check کریں
3. Supabase dashboard دیکھیں
4. Dependencies re-install کریں

---

## ✅ **Success Indicators**

آپ کو یہ نظر آنا چاہیے:
- ✅ "Connected to Supabase PostgreSQL"
- ✅ Recommendation output
- ✅ Supabase میں 3 tables
- ✅ Products data visible

**اگر سب ✅ ہیں = Setup Complete! 🎉**
