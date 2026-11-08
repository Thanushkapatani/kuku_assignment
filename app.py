import streamlit as st
import zipfile, re, os, json, io, csv
from pathlib import Path

DRAMA = {
 "hook": ["what do you mean", "not anymore", "because he is marrying", "you should turn around",
          "i know your secret", "you're", "you are", "stop", "help", "no", "why", "how dare",
          "who are you", "what", "never", "can't", "cannot", "impossible", "dead", "pregnant",
          "marrying", "betray", "betrayed", "murder", "kill", "secret", "truth", "shocked"],
 "cliff": ["but", "unless", "if you", "you don't know", "what happens", "who", "why", "secret",
           "will you", "i swear", "i'll", "i will", "never", "wait", "stop", "the truth",
           "before", "tonight", "tomorrow", "surprise", "one condition", "not yet"],
 "emotion": ["shock", "shocked", "tears", "cry", "heartbroken", "furious", "outrage", "betray",
             "slap", "scream", "gasp", "plead", "desperate", "threat", "revenge", "love",
             "hate", "marry", "wedding", "divorce", "pregnant", "blood", "gun", "die", "death",
             "father", "mother", "sister", "husband", "wife", "duke", "soldier", "secret",
             "lie", "cheat", "abandon", "humiliate", "kneel", "beg", "revenge"]
}
TS = re.compile(r"Start:\s*\(([^)]+)\)\s*\|\s*End:\s*\(([^)]+)\)")
def sec(s):
    m=re.match(r"(?:(\d+):)?(\d{2}):(\d{2})(?:\.(\d+))?$",s.strip())
    if not m:
        p=s.strip().split(":")
        try: return float(p[-2])*60+float(p[-1])
        except: return 0.0
    h,mm,ss,frac=m.groups()
    return (int(h or 0)*3600+int(mm)*60+int(ss)+float("0."+(frac or "0")))
def stamp(x):
    x=max(0,int(round(x)))
    return f"{x//60:02d}:{x%60:02d}"
def parse(text):
    matches=list(TS.finditer(text)); ev=[]
    for i,m in enumerate(matches):
        a,b=sec(m.group(1)),sec(m.group(2))
        tail=text[m.end():matches[i+1].start() if i+1<len(matches) else min(len(text),m.end()+600)]
        tail=re.sub(r"\n+", " ", tail).strip()
        # Prefer quoted dialogue, otherwise retain the action/camera description
        qs=re.findall(r'"([^"]{2,})"',tail)
        desc=" ".join(qs) if qs else tail[:350]
        desc=re.sub(r"\*\*|\\", "", desc).strip()
        if b>=a: ev.append({"start":a,"end":b,"text":desc})
    return ev
def score_window(events,start,end):
    inside=[e for e in events if e["end"]>=start and e["start"]<=end]
    if not inside: return None
    joined=" ".join(e["text"].lower() for e in inside)
    hook_events=[e for e in inside if e["start"]<=start+3 and e["end"]>=start]
    hooktxt=" ".join(e["text"].lower() for e in hook_events)
    end_events=[e for e in inside if e["end"]>=end-8]
    clifftxt=" ".join(e["text"].lower() for e in end_events)
    h=sum(1 for w in DRAMA["hook"] if w in hooktxt)
    c=sum(1 for w in DRAMA["cliff"] if w in clifftxt)
    emo=sum(1 for w in DRAMA["emotion"] if w in joined)
    dialogue=sum(1 for e in inside if '"' in e["text"])
    density=min(10,len(inside)/3)
    total=round(h*2.2+c*2.0+min(emo,12)*1.1+density+min(dialogue,8)*.35,2)
    # explainable evidence
    hook=next((e["text"] for e in hook_events if e["text"]), "Opening visual/action in this segment")
    cliff=next((e["text"] for e in reversed(end_events) if e["text"]), "Unresolved dramatic beat near the cut")
    return {"start":start,"end":end,"score":total,"hook":hook[:220],"cliffhanger":cliff[:220],
            "why":f"{len(inside)} timed beats; {emo} emotional keyword matches; hook={h}, cliffhanger={c} signal matches."}
def analyze_episode(filename,text):
    events=parse(text)
    if not events: return []
    last=max(e["end"] for e in events)
    # Sliding windows: 20-60 seconds; rank candidates with a preference for 30-45 sec.
    candidates=[]
    for dur in (25,30,35,40,45,50,55,60):
        t=0
        while t+dur<=last:
            r=score_window(events,t,t+dur)
            if r: 
                r["duration"]=dur
                candidates.append(r)
            t+=5
    # de-duplicate heavily overlapping options; keep up to 3 varied moments
    candidates.sort(key=lambda x:x["score"],reverse=True)
    chosen=[]
    for c in candidates:
        if all(abs(c["start"]-x["start"])>=18 for x in chosen):
            chosen.append(c)
        if len(chosen)==3: break
    ep=re.search(r"episode-(\d+)",filename)
    epno=int(ep.group(1)) if ep else filename
    for i,c in enumerate(chosen,1):
        c.update({"episode":epno,"rank_in_episode":i,"start_time":stamp(c["start"]),"end_time":stamp(c["end"])})
    return chosen

st.set_page_config(page_title="Kuku Promo Finder",page_icon="🎬",layout="wide")
st.title("🎬 Kuku Promo Finder")
st.caption("A lightweight, repeatable screenplay scanner that ranks candidate 20–60 second promo windows.")
uploaded=st.file_uploader("Upload the screenplay ZIP (50 episode .txt files)",type=["zip"])
if uploaded:
    with zipfile.ZipFile(uploaded) as z:
        files=[n for n in z.namelist() if n.lower().endswith(".txt")]
        all_results=[]
        for n in files:
            raw=z.read(n).decode("utf-8",errors="replace")
            all_results.extend(analyze_episode(os.path.basename(n),raw))
    all_results.sort(key=lambda x:x["score"],reverse=True)
    st.success(f"Analysed {len(files)} episode files and generated {len(all_results)} candidate promos.")
    st.subheader("Top-ranked candidates")
    for r in all_results[:15]:
        with st.expander(f"#{all_results.index(r)+1} · Episode {r['episode']} · {r['start_time']}–{r['end_time']} · score {r['score']}"):
            st.write("**Hook / opening beat:**",r["hook"])
            st.write("**Cliffhanger / ending beat:**",r["cliffhanger"])
            st.write("**Why it may work:**",r["why"])
    st.download_button("Download all results (JSON)",json.dumps(all_results,indent=2),file_name="promo_candidates.json",mime="application/json")
    csvbuf=io.StringIO()
    fields=["episode","rank_in_episode","start_time","end_time","duration","score","hook","cliffhanger","why"]
    w=csv.DictWriter(csvbuf,fieldnames=fields);w.writeheader()
    for r in all_results:w.writerow({k:r.get(k,"") for k in fields})
    st.download_button("Download all results (CSV)",csvbuf.getvalue(),file_name="promo_candidates.csv",mime="text/csv")
else:
    st.info("Upload the supplied ZIP to analyse all episodes. The app does not edit video; it only proposes timestamped moments.")
st.markdown("---")
st.markdown("**How ranking works:** timed dialogue/action beats are parsed from each screenplay. Candidate windows of 25–60 seconds are scored using opening-hook, emotional-intensity and unresolved-ending keyword signals plus beat density. Scores are a triage aid, not a prediction of social performance.")
