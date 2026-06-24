import urllib.request
import re
import os
import time
import json

OUTPUT_DIR = "/root/the-donna-project/kelvins-donna/transcripts/raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# All known Fandom transcript pages for Suits
EPISODE_URLS = {
    "S01E01": "https://suits.fandom.com/wiki/Pilot_-_Transcript",
    "S01E02": "https://suits.fandom.com/wiki/Errors_and_Omissions_-_Transcript",
    "S01E03": "https://suits.fandom.com/wiki/Inside_Track_-_Transcript",
    "S01E04": "https://suits.fandom.com/wiki/Dirty_Little_Secrets_-_Transcript",
    "S01E05": "https://suits.fandom.com/wiki/Bail_Out_-_Transcript",
    "S01E06": "https://suits.fandom.com/wiki/Tricks_of_the_Trade_-_Transcript",
    "S01E07": "https://suits.fandom.com/wiki/Play_the_Man_-_Transcript",
    "S01E08": "https://suits.fandom.com/wiki/Identity_Crisis_-_Transcript",
    "S01E09": "https://suits.fandom.com/wiki/Undefeated_-_Transcript",
    "S01E10": "https://suits.fandom.com/wiki/The_Shelf_Life_-_Transcript",
    "S01E11": "https://suits.fandom.com/wiki/Rules_of_the_Game_-_Transcript",
    "S01E12": "https://suits.fandom.com/wiki/Dog_Fight_-_Transcript",
}

# Context classification rules
def classify_context(block):
    text = block.get("line","").lower()
    who = block.get("to","").lower()

    tags = []

    # WHO
    if any(x in who for x in ["harvey","specter"]):
        tags.append("TO:HARVEY")
    elif any(x in who for x in ["mike","ross"]):
        tags.append("TO:MIKE")
    elif any(x in who for x in ["louis","litt"]):
        tags.append("TO:LOUIS")
    elif any(x in who for x in ["jessica","pearson"]):
        tags.append("TO:JESSICA")
    elif any(x in who for x in ["rachel","zane"]):
        tags.append("TO:RACHEL")
    elif any(x in who for x in ["client","opposing","counsel","mr.","ms."]):
        tags.append("TO:CLIENT")
    else:
        tags.append("TO:UNKNOWN")

    dialogue = block.get("line","").lower()

    # REGISTER
    if any(x in dialogue for x in ["i already","already taken","already handled","already on it"]):
        tags.append("REGISTER:PREEMPTIVE")
    if any(x in dialogue for x in ["let me be clear","here's what","here is what"]):
        tags.append("REGISTER:AUTHORITY")
    if any(x in dialogue for x in ["i don't know","not sure","find out","confirm that","get back to you"]):
        tags.append("REGISTER:RECOVERY")
    if any(x in dialogue for x in ["love","miss","feel","hurt","sorry","okay","okay?"]):
        tags.append("REGISTER:EMOTIONAL")
    if any(x in dialogue for x in ["harvey","he needs","he wants","he would","protect"]):
        tags.append("REGISTER:PROTECTIVE")
    if any(x in dialogue for x in ["absolutely not","no","won't","can't","that's not"]):
        tags.append("REGISTER:BOUNDARY")
    if any(x in dialogue for x in ["ha","funny","please","really?","oh come on"]):
        tags.append("REGISTER:WIT")
    if any(x in dialogue for x in ["i'm donna","i know everything","that's what i do"]):
        tags.append("REGISTER:IDENTITY")

    return tags

def fetch_transcript(ep_id, url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  FAILED {ep_id}: {e}")
        return []

    # Extract content
    start = html.find('class="mw-parser-output"')
    if start == -1:
        start = html.find('DONNA:')
    chunk = html[start:start+500000]
    chunk = re.sub(r'<br\s*/?>', '\n', chunk)
    chunk = re.sub(r'<[^>]+>', '', chunk)
    chunk = re.sub(r'&amp;', '&', chunk)
    chunk = re.sub(r'&quot;', '"', chunk)
    chunk = re.sub(r'&#39;', "'", chunk)
    chunk = re.sub(r'&nbsp;', ' ', chunk)

    lines = chunk.split('\n')
    donna_blocks = []
    prev_speaker = ""
    prev_line = ""
    next_line = ""

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # Stage directions — extract for context
        stage = ""
        if line.startswith('[') and line.endswith(']'):
            stage = line
            continue

        # Detect speaker
        speaker_match = re.match(r'^([A-Z][A-Z\s\.]{1,25}):\s+(.+)$', line)
        if speaker_match:
            speaker = speaker_match.group(1).strip()
            dialogue = speaker_match.group(2).strip()

            if speaker == "DONNA" and len(dialogue) > 4:
                # Get surrounding context
                context_before = prev_line
                context_after = lines[i+1].strip() if i+1 < len(lines) else ""

                block = {
                    "episode": ep_id,
                    "line": dialogue,
                    "to": prev_speaker,
                    "context_before": context_before,
                    "context_after": context_after,
                    "stage_direction": stage
                }
                block["tags"] = classify_context(block)
                donna_blocks.append(block)

            prev_speaker = speaker
            prev_line = line

    print(f"  {ep_id}: {len(donna_blocks)} Donna lines extracted")
    return donna_blocks

all_donna_lines = []

for ep_id, url in EPISODE_URLS.items():
    print(f"Fetching {ep_id}...")
    blocks = fetch_transcript(ep_id, url)
    all_donna_lines.extend(blocks)
    time.sleep(2)

# Save raw JSON
with open(f"{OUTPUT_DIR}/donna_lines_s01.json", "w") as f:
    json.dump(all_donna_lines, f, indent=2)

print(f"\nTOTAL Donna lines extracted: {len(all_donna_lines)}")
print(f"Saved to {OUTPUT_DIR}/donna_lines_s01.json")

# Tag frequency report
from collections import Counter
all_tags = []
for b in all_donna_lines:
    all_tags.extend(b.get("tags", []))
tag_counts = Counter(all_tags)
print("\nTag frequency:")
for tag, count in tag_counts.most_common():
    print(f"  {tag}: {count}")
