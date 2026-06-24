import urllib.request
import re
import os
import time
import json
from collections import Counter

OUTPUT_DIR = "/root/the-donna-project/kelvins-donna/transcripts/raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

BASE = "https://www.springfieldspringfield.co.uk/view_episode_scripts.php?tv-show=suits&episode="

# All 134 episodes
EPISODES = []
schedule = {1:12, 2:16, 3:16, 4:16, 5:16, 6:16, 7:10, 8:16, 9:10}
for season, count in schedule.items():
    for ep in range(1, count+1):
        EPISODES.append(f"s{season:02d}e{ep:02d}")

def classify(line, prev_speaker, prev_line, next_line):
    l = line.lower()
    p = prev_speaker.upper()
    tags = []

    # WHO she's talking to
    if p in ["HARVEY","SPECTER"]: tags.append("TO:HARVEY")
    elif p in ["MIKE","ROSS"]: tags.append("TO:MIKE")
    elif p in ["LOUIS","LITT"]: tags.append("TO:LOUIS")
    elif p in ["JESSICA","PEARSON"]: tags.append("TO:JESSICA")
    elif p in ["RACHEL","ZANE"]: tags.append("TO:RACHEL")
    elif p == "": tags.append("TO:OPENING")
    else: tags.append(f"TO:OTHER({prev_speaker.strip()})")

    # REGISTER
    if any(x in l for x in ["already","taken care","handled it","done it","i know","knew you"]): tags.append("REG:PREEMPTIVE")
    if any(x in l for x in ["here's what","let me be clear","listen to me","what's happening"]): tags.append("REG:AUTHORITY")
    if any(x in l for x in ["find out","confirm","get back to you","let me check","one moment"]): tags.append("REG:RECOVERY")
    if any(x in l for x in ["i love","i miss","i'm sorry","hurt","feel","okay?","are you okay"]): tags.append("REG:EMOTIONAL")
    if any(x in l for x in ["harvey","he needs","protect","don't let","won't let","not on my watch"]): tags.append("REG:PROTECTIVE")
    if any(x in l for x in ["absolutely not","no.","won't","can't do","that's not","stop"]): tags.append("REG:BOUNDARY")
    if any(x in l for x in ["really?","oh come on","please","you're kidding","seriously?"]): tags.append("REG:WIT")
    if any(x in l for x in ["i'm donna","i know everything","that's what i do","i read","i analyze"]): tags.append("REG:IDENTITY")
    if any(x in l for x in ["you need to","you should","if i were you","what you need"]): tags.append("REG:COUNSEL")
    if any(x in l for x in ["appointment","schedule","he's in","he's not","call back","message"]): tags.append("REG:GATEKEEPER")

    return tags

def fetch_episode(ep_id):
    url = BASE + ep_id
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return [], str(e)

    content = re.search(r'class="scrolling-script-container">(.*?)</div>', html, re.DOTALL)
    if not content:
        return [], "no-content"

    raw = content.group(1)
    raw = re.sub(r'<br\s*/?>', '\n', raw)
    raw = re.sub(r'<[^>]+>', '', raw)
    raw = re.sub(r'&amp;', '&', raw)
    raw = re.sub(r'&quot;', '"', raw)
    raw = re.sub(r'&#39;', "'", raw)
    raw = re.sub(r'&nbsp;', ' ', raw)

    lines = [l.strip() for l in raw.split('\n') if l.strip()]
    donna_blocks = []
    prev_speaker = ""
    prev_line = ""

    for i, line in enumerate(lines):
        donna_match = re.match(r"^Donna[,\s]+(.+)$", line, re.IGNORECASE)
        if donna_match:
            dialogue = donna_match.group(1).strip()
            next_line = lines[i+1] if i+1 < len(lines) else ""
            tags = classify(dialogue, prev_speaker, prev_line, next_line)
            donna_blocks.append({
                "ep": ep_id,
                "line": dialogue,
                "prev_speaker": prev_speaker,
                "context_before": prev_line,
                "context_after": next_line,
                "tags": tags
            })
        else:
            # Detect current speaker for next iteration
            speaker_match = re.match(r'^([A-Z][a-zA-Z\s]{1,20})[,\.\s]+', line)
            if speaker_match and len(line) > 5:
                prev_speaker = speaker_match.group(1).strip()
            prev_line = line

    return donna_blocks, "ok"

print(f"Extracting Donna lines from {len(EPISODES)} episodes...\n")
all_lines = []
failed = []

for ep in EPISODES:
    blocks, status = fetch_episode(ep)
    all_lines.extend(blocks)
    if status != "ok":
        failed.append((ep, status))
        print(f"  {ep}: FAILED — {status}")
    else:
        print(f"  {ep}: {len(blocks)} lines")
    time.sleep(1.5)

# Save everything
with open(f"{OUTPUT_DIR}/donna_all_lines.json", "w") as f:
    json.dump(all_lines, f, indent=2)

print(f"\n{'='*50}")
print(f"TOTAL Donna lines extracted: {len(all_lines)}")
print(f"Failed episodes: {len(failed)}")

# Tag report
all_tags = []
for b in all_lines: all_tags.extend(b.get("tags", []))
counts = Counter(all_tags)
print("\nTag frequency across all 9 seasons:")
for tag, count in counts.most_common():
    print(f"  {tag}: {count}")
