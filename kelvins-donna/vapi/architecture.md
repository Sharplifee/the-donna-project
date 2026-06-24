# Kelvins Donna — Full Architecture
## Read + Write | Live Intel | Pipeline Integration

---

## WHAT SHE IS

Not a voice agent. A fully operational layer between Kelvin and his pipeline.

She receives calls, makes calls, reads live deal data, speaks from it, and writes outcomes back.
Kelvin touches only what needs him. Everything else is handled.

---

## DATA FLOW

```
INBOUND CALL
     │
     ▼
VAPI (Donna persona + system prompt v2)
     │
     ├── READS from ProspectPlus on call start
     │   ├── Caller ID → match to lead record
     │   ├── Lead status, last touchpoint, deal stage
     │   ├── Kelvin's notes on this person
     │   └── Active listings relevant to this lead
     │
     ├── OPERATES during call
     │   ├── Qualifies, nurtures, schedules
     │   ├── Answers from live context
     │   └── Handles or escalates to Kelvin
     │
     └── WRITES on call end (end-of-call webhook)
         ├── Call summary → ProspectPlus lead record
         ├── Outcome tag (qualified / follow-up / not interested / appointment set)
         ├── Next action + date
         └── Flag to Kelvin if escalation needed

OUTBOUND CALL
     │
     ▼
VAPI triggered by ProspectPlus workflow
     ├── Lead pulled from pipeline queue
     ├── Donna context loaded (lead history, deal stage, last contact)
     ├── Call placed
     └── Same write-back on completion
```

---

## INTEGRATIONS REQUIRED

### 1. ProspectPlus → VAPI (read on call start)
- Caller ID lookup against lead database
- Return: lead name, status, stage, Kelvin notes, relevant listings
- Method: VAPI server URL webhook → ProspectPlus API → inject into call context

### 2. VAPI → ProspectPlus (write on call end)
- End-of-call webhook fires to Supabase edge function
- Edge function parses transcript + outcome
- Writes to ProspectPlus lead record:
  - call_log entry (date, duration, summary)
  - status update if changed
  - next_action + next_action_date
  - escalate_to_kelvin boolean

### 3. Twilio number (385-213-9960 — shared with Cliff)
- VAPI routing rule: if caller_id matches ProspectPlus lead → Donna
- If not matched → Cliff (existing behavior)
- Outbound: Donna dials from same number on behalf of Kelvin

### 4. Kelvin briefing (internal Donna function)
- Daily summary pushed to Kelvin via SMS (Sendblue) or iMessage
- "Here's where your pipeline is today. Three follow-ups needed. One appointment confirmed."
- Triggered by morning cron or on-demand

---

## SUPABASE EDGE FUNCTION — donna-eoc (end of call)

Receives VAPI post-call webhook, extracts:
- transcript
- call_duration
- caller_id
- call_outcome (from Donna's structured close)

Writes to ProspectPlus:
- lead_calls table: new row with summary + outcome
- leads table: updated last_contact, status, next_action
- kelvin_flags table: if escalation detected

---

## VAPI TOOL FUNCTIONS (in-call)

Donna needs these tools available during live calls:

### get_lead_context(phone_number)
Pulls lead record from ProspectPlus by phone
Returns: name, stage, history, listings, Kelvin notes

### check_calendar(date_range)
Checks Kelvin's availability for appointment setting
Returns: open slots in next 7 days

### log_appointment(lead_id, datetime, type)
Books appointment in Kelvin's calendar
Writes confirmation back to ProspectPlus

### flag_for_kelvin(lead_id, reason, urgency)
Creates escalation flag
Sends Kelvin SMS with summary

---

## BUILD ORDER

1. ☐ ProspectPlus lead lookup endpoint (phone → lead record)
2. ☐ donna-eoc Supabase edge function
3. ☐ VAPI tool definitions (get_lead_context, check_calendar, log_appointment, flag_for_kelvin)
4. ☐ VAPI assistant config with tools wired
5. ☐ Routing rule on 385-213-9960 (Donna vs Cliff by caller ID)
6. ☐ Outbound calling trigger from ProspectPlus pipeline
7. ☐ Kelvin daily briefing (Sendblue SMS)
8. ☐ Voice selection + ElevenLabs config
9. ☐ Live test with real lead

---

## WHAT KELVIN EXPERIENCES

A lead calls. Donna answers. She already knows who they are.
She handles it, logs it, and Kelvin gets a summary.

Kelvin calls Donna. She briefs him on his day, his pipeline, who needs attention.
She already knows everything. He just has to show up.

A lead goes cold. Donna calls them outbound from the pipeline queue.
Outcome logged. Kelvin never had to think about it.

That's the build. That's the system.
