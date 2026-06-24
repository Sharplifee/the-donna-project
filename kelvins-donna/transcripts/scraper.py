import urllib.request
import time
import re
import os

BASE_URL = "https://transcripts.foreverdreaming.org"
FORUM_URL = f"{BASE_URL}/viewforum.php?f=189"
OUTPUT_DIR = "/root/the-donna-project/kelvins-donna/transcripts/raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}")
        return ""

# Pull the forum index to get all episode links
print("Fetching forum index...")
pages = [
    f"{BASE_URL}/viewforum.php?f=189&start=0",
    f"{BASE_URL}/viewforum.php?f=189&start=25",
    f"{BASE_URL}/viewforum.php?f=189&start=50",
    f"{BASE_URL}/viewforum.php?f=189&start=75",
    f"{BASE_URL}/viewforum.php?f=189&start=100",
    f"{BASE_URL}/viewforum.php?f=189&start=125",
]

episode_links = []
for page_url in pages:
    html = fetch(page_url)
    found = re.findall(r'href="(viewtopic\.php\?[^"]+)"[^>]*>[^<]*\d+x\d+', html)
    for link in found:
        full = BASE_URL + "/" + link.replace("&amp;", "&")
        if full not in episode_links:
            episode_links.append(full)
    time.sleep(1)

print(f"Found {len(episode_links)} episode links")
for l in episode_links[:10]:
    print(f"  {l}")
