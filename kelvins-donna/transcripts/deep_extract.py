import urllib.request
import re
import json
import time
import os
from collections import Counter

OUTPUT_DIR = "/root/the-donna-project/kelvins-donna/transcripts/raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
BASE = "https://www.springfieldspringfield.co.uk/view_episode_scripts.php?tv-show=suits&episode="

schedule = {1:12, 2:16, 3:16, 4:16, 5:16, 6:16, 7:10, 8:16, 9:10}
EPISODES = [f"s{s:02d}e{e:02d}" for s,c in schedule.items() for e in range(1,c+1)]

# Known Donna speech triggers — her lines follow these patterns
# Pattern 1: "Donna, [something]" then the NEXT sentence is her reply
# Pattern 2: "Donna [verb]s" — she's doing something, not speaking
# Pattern 3: Direct quotes after "Donna:" — rare in this format
# Pattern 4: Lines that are clearly her voice following context about her

def extract_donna_dialogue(sentences):
    """
    Springfield Springfield writes in prose. Donna's actual words appear:
    1. Immediately after someone addresses her ("Donna, [question/request]") — next sentence(s) are her response
    2. In compound sentences: "Donna, can you X? Absolutely. And after that..." — her words follow
    3. As standalone declaratives in scenes clearly about her
    """
    donna_exchanges = []
    
    i = 0
    while i < len(sentences):
        s = sentences[i]
        
        # Pattern 1: Someone addresses Donna directly
        # "Not now, Donna." / "Donna, we need to..." / "Donna?"
        address_match = re.search(r'\bDonna[,\.\?\!]?\s*$', s) or re.search(r'^[^.]*\bDonna[,\.\?\!]\s+\w', s)
        
        if address_match:
            # Collect speaker context (who said this)
            addressed_by = ""
            # Look back for speaker signal
            for back in range(max(0,i-3), i):
                prev = sentences[back]
                # Common patterns that signal speaker change
                if any(x in prev.lower() for x in ['harvey', 'specter', 'mike', 'louis', 'jessica', 'rachel', 'samantha']):
                    addressed_by = prev[:60]
                    break
            
            # Collect Donna's response — next 1-4 sentences until another name appears
            donna_response = []
            j = i + 1
            while j < len(sentences) and j < i + 5:
                next_s = sentences[j]
                # Stop if we hit another direct address or clear scene break
                if re.search(r'\b(Harvey|Mike|Louis|Jessica|Rachel|Samantha)\b', next_s) and len(next_s) < 40:
                    break
                if re.search(r'^(Harvey|Mike|Louis|Jessica|Rachel|Samantha)[,\.]', next_s):
                    break
                donna_response.append(next_s)
                j += 1
            
            if donna_response:
                full_response = ' '.join(donna_response).strip()
                if len(full_response) > 8:
                    donna_exchanges.append({
                        "trigger": s.strip(),
                        "donna_says": full_response,
                        "addressed_by_context": addressed_by,
                        "sentences_after": j - (i+1)
                    })
        
        # Pattern 2: Compound sentence where Donna speaks inline
        # "Donna, can you X? Absolutely. Y." — extract the reply portion
        inline = re.search(r'\bDonna[,\s][^?!.]{5,60}[?!]\s+(.{10,200})', s)
        if inline:
            response = inline.group(1).strip()
            if len(response) > 10 and not re.search(r'\bDonna\b', response):
                donna_exchanges.append({
                    "trigger": s[:80],
                    "donna_says": response,
                    "addressed_by_context": "",
                    "sentences_after": 0
                })
        
        i += 1
    
    return donna_exchanges


def deep_classify(exchange, ep_id):
    """Full contextual classification of a Donna exchange"""
    trigger = exchange["trigger"].lower()
    says = exchange["donna_says"].lower()
    context = exchange["addressed_by_context"].lower()
    
    tags = []
    
    # SEASON arc
    season = int(ep_id[1:3])
    if season <= 2: tags.append("ARC:EARLY-DONNA")
    elif season <= 5: tags.append("ARC:MID-DONNA")
    elif season <= 7: tags.append("ARC:PEAK-DONNA")
    else: tags.append("ARC:COO-DONNA")
    
    # WHO is addressing her
    if 'harvey' in trigger or 'harvey' in context: tags.append("WHO:HARVEY")
    elif 'mike' in trigger or 'mike' in context: tags.append("WHO:MIKE")
    elif 'louis' in trigger or 'louis' in context: tags.append("WHO:LOUIS")
    elif 'jessica' in trigger or 'jessica' in context: tags.append("WHO:JESSICA")
    elif 'rachel' in trigger or 'rachel' in context: tags.append("WHO:RACHEL")
    elif 'samantha' in trigger or 'samantha' in context: tags.append("WHO:SAMANTHA")
    else: tags.append("WHO:UNKNOWN")
    
    # WHAT HARVEY/OTHERS NEED from her
    if any(x in trigger for x in ['can you', 'need you', 'get me', 'find out', 'schedule']): tags.append("REQUEST:TASK")
    if any(x in trigger for x in ['what do you', 'how do you', 'why', 'what happened']): tags.append("REQUEST:INTEL")
    if any(x in trigger for x in ['are you okay', 'how are you', 'you alright']): tags.append("REQUEST:PERSONAL")
    if any(x in trigger for x in ['donna?', 'donna!']): tags.append("REQUEST:SUMMON")
    
    # HOW SHE RESPONDS
    if any(x in says for x in ['already', 'taken care', 'done', 'handled', 'way ahead']): tags.append("DONNA:PREEMPTIVE")
    if any(x in says for x in ['absolutely', 'of course', "i'll", "i will", "i've got"]): tags.append("DONNA:OWNERSHIP")
    if any(x in says for x in ["i know", "i knew", "i could tell", "i noticed", "you're", "you are"]): tags.append("DONNA:READS-PEOPLE")
    if any(x in says for x in ['harvey', 'he needs', 'he wants', "he's going", 'protect']): tags.append("DONNA:PROTECTS-HARVEY")
    if any(x in says for x in ['i love', "i'm sorry", 'hurt', 'feel', 'miss you']): tags.append("DONNA:EMOTIONAL")
    if any(x in says for x in ['no.', "won't", "not going to", "not a chance", "absolutely not"]): tags.append("DONNA:HOLDS-LINE")
    if any(x in says for x in ['really?', 'please', 'come on', "you're kidding", 'seriously']): tags.append("DONNA:WIT")
    if any(x in says for x in ["i'm donna", "i know everything", "that's what i do", "i read"]): tags.append("DONNA:IDENTITY-STATEMENT")
    if any(x in says for x in ['you need to', 'you should', 'if i were', 'what you need']): tags.append("DONNA:COUNSELS")
    if any(x in says for x in ['appointment', 'schedule', "he's in", "he's not in", 'message']): tags.append("DONNA:GATEKEEPS")
    if any(x in says for x in ['let me find out', 'confirm', 'get back to you', 'one moment', 'check']): tags.append("DONNA:RECOVERS-GRACEFULLY")
    
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
    sentences = re.split(r'<br\s*/?>', raw)
    sentences = [re.sub(r'<[^>]+>','',s).strip() for s in sentences]
    sentences = [re.sub(r'&amp;','&',re.sub(r'&#39;',"'",re.sub(r'&quot;','"',s))) for s in sentences]
    sentences = [s for s in sentences if len(s) > 3]

    exchanges = extract_donna_dialogue(sentences)
    
    results = []
    for ex in exchanges:
        tags = deep_classify(ex, ep_id)
        results.append({
            "ep": ep_id,
            "trigger": ex["trigger"],
            "donna_says": ex["donna_says"],
            "context": ex["addressed_by_context"],
            "tags": tags
        })
    
    return results, "ok"


print(f"Deep-extracting Donna exchanges from {len(EPISODES)} episodes...\n")
all_exchanges = []
failed = []

for ep in EPISODES:
    exchanges, status = fetch_episode(ep)
    all_exchanges.extend(exchanges)
    if status != "ok":
        failed.append((ep, status))
        print(f"  {ep}: FAILED — {status}")
    else:
        print(f"  {ep}: {len(exchanges)} exchanges")
    time.sleep(1.5)

with open(f"{OUTPUT_DIR}/donna_exchanges_deep.json", "w") as f:
    json.dump(all_exchanges, f, indent=2)

print(f"\n{'='*50}")
print(f"TOTAL exchanges: {len(all_exchanges)}")
print(f"Failed: {len(failed)}")

all_tags = []
for ex in all_exchanges: all_tags.extend(ex.get("tags",[]))
counts = Counter(all_tags)
print("\nFull contextual tag breakdown:")
for tag, count in counts.most_common():
    print(f"  {tag}: {count}")
