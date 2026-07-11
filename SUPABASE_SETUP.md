# Supabase Setup Guide

## 📋 **Setup Steps**

### 1. Create Supabase Project
1. Go to [supabase.com](https://supabase.com)
2. Create new project
3. Note down:
   - Project URL
   - Anon/Public Key
   - Database Password

### 2. Get Database Connection String
1. Go to Project Settings → Database
2. Copy the **Connection String** (URI format)
3. Replace `[YOUR-PASSWORD]` with your database password

Example:
```
postgresql://postgres:your_password@db.abc123xyz.supabase.co:5432/postgres
```

### 3. Configure Environment Variables
1. Create `.env` file in project root:
```bash
cp .env.example .env
```

2. Fill in your Supabase credentials:
```env
SUPABASE_URL=https://abc123xyz.supabase.co
SUPABASE_KEY=your_anon_key_here
SUPABASE_DB_URL=postgresql://postgres:your_password@db.abc123xyz.supabase.co:5432/postgres
```

### 4. Install Dependencies
```bash
pip install psycopg2-binary python-dotenv
```

### 5. Initialize Database
Tables will be created automatically when you first run the agents:
```bash
python test_agents_e2e.py
```

## 📊 **Tables Created**

### `products`
Stores cleaned product data from NLP agent.

### `category_patterns`
Stores learned pricing patterns per category.

### `recommendations`
Stores analytics agent outputs.

## ✅ **Verify Setup**

Check if tables were created:
1. Go to Supabase Dashboard
2. Click "Table Editor"
3. You should see: `products`, `category_patterns`, `recommendations`

## 🎯 **Using Any Category**

System کسی بھی category کے ساتھ کام کرتا ہے:

```python
# Example 1: Electronics
recommendation = analytics_agent.analyze(
    product_name="gaming headset",
    category="electronics",
    nlp_output=nlp_output
)

# Example 2: Fashion
recommendation = analytics_agent.analyze(
    product_name="leather jacket",
    category="fashion",
    nlp_output=nlp_output
)

# Example 3: Home & Kitchen
recommendation = analytics_agent.analyze(
    product_name="air fryer",
    category="home_kitchen",
    nlp_output=nlp_output
)
```

## 💡 **Tips**

1. **Category names consistent رکھیں**
   - ✅ "electronics"
   - ❌ "Electronics", "electronic"

2. **20-30 products scrape کریں** ہر category کے لیے
   - Better learning
   - Higher confidence

3. **Check Supabase Dashboard** regularly
   - Monitor data growth
   - View recommendations
   - Track category patterns

## 🔒 **Security**

- ⚠️ **Never commit `.env` file** to git
- ✅ `.env` is already in `.gitignore`
- ✅ Use `.env.example` as template
