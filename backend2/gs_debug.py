import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def save(url, filename):
    html = requests.get(url, headers=HEADERS).text
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print("SAVED:", filename)

# 1) GlobalSources search page
save(
    "https://www.globalsources.com/search?query=WH-1000XM5",
    "gs_search.html"
)

# 2) One product page (you will paste link here later)
save(
    "https://www.globalsources.com/Wireless-earphone/Wireless-Headphones-1226409527p.htm",
    "gs_product.html"
)
