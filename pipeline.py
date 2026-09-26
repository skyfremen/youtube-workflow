#!/usr/bin/env python3
"""Wacky Dramas common deterministic V2 planner/production bridge."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
BG=ROOT/"data/backgrounds.json"; HIST=ROOT/"data/history.json"; CTX=ROOT/"content/context.json"; PLANNER_ANALYTICS=ROOT/"content/planner-analytics.json"; PUBLISH_SLOTS=ROOT/"data/publish-slots.json"
REQS=ROOT/"content/requests"; EXECS=ROOT/"content/executions"; FAILS=ROOT/"content/failures"; DRAFTS=ROOT/"content/drafts"
REQUEST_VERSION=2; EXECUTION_VERSION=2; RESULT_VERSION=2; CONTEXT_VERSION=3
RECENT_LIMIT=25; MIN_CATEGORY_BACKGROUNDS=3; MIN_BG=60.0; MAX_SEGMENT=100.0
MAX_CONTEXT_BYTES=40000; MAX_PLANNER_ANALYTICS_BYTES=16000
MIN_NARR=45.0; MAX_NARR=65.0; BASE_WORDS_PER_SEC=2.7; TTS_SPEED=1.75
SGT=ZoneInfo("Asia/Singapore"); SLOT_BUFFER=timedelta(minutes=10); YOUTUBE_SCAN_LIMIT=250
EXPECTED_YOUTUBE_CHANNEL_ID="UCvrq2m9G4yrwPfL_X-QPzMA"
DEFAULT_EMOJIS=["😳","💬","🔥","👀"]
EMOJI_MAP={"shock":"😳","surprise":"😮","argument":"💢","anger":"😡","betrayal":"💔","suspicion":"🤨","secret":"🤫","evidence":"📱","money":"💰","revenge":"😈","embarrassment":"😬","victory":"😎","funny":"😂","romance":"❤️","panic":"😱","confusion":"😵","disbelief":"🤯","warning":"⚠️","celebration":"🎉","awkward":"🙃"}
NATURAL={"natural","neutral","conversational","warm","calm"}; EXPRESSIVE={"expressive","dramatic","comedy","sarcastic","dramatic_comedy","absurd"}; TONES=NATURAL|EXPRESSIVE
HOOK_TYPES={"accusation","discovery","contradiction","money_stakes","social_exposure","urgency","confession","consequence_first"}
DRAFT_RE=re.compile(r"^draft-[A-Za-z0-9-]{8,96}$"); CID_RE=re.compile(r"^wd-[0-9a-f]{24}$"); RID_RE=re.compile(r"^rq-[0-9a-f]{24}$"); EID_RE=re.compile(r"^ex-[0-9a-f]{24}$"); SHA40=re.compile(r"^[0-9a-f]{40}$")
CONTRACT={"name":"wacky-dramas-production-v2","request_version":2,"execution_version":2,"result_version":2,"visibility":"private_scheduled","request_path":"content/requests/{request_id}.json","execution_path":"content/executions/{execution_id}.json","result_path":"content/results/{content_id}.json","registry_path":"data/backgrounds.json"}
CONTRACT_HASH=hashlib.sha256(json.dumps(CONTRACT,sort_keys=True,separators=(",",":")).encode()).hexdigest()

class VError(ValueError):
    def __init__(self,code,field,observed,required,repairable=True):
        self.code,self.field,self.observed,self.required,self.repairable=code,field,observed,required,repairable
        super().__init__(f"{code} field={field} observed={observed!r} required={required}")

class DraftValidationError(VError):
    def __init__(self,violations):
        self.violations=list(violations)
        super().__init__("DRAFT_VALIDATION_FAILED","winners",f"violations={len(self.violations)}","all winners satisfy planner-repairable constraints",True)

def pretty(x): return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode()
def canonical(x): return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()
def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def read_draft(p):
    try: return read(p)
    except json.JSONDecodeError as e: raise VError("DRAFT_JSON_INVALID","$",f"{e.msg}; line={e.lineno}; column={e.colno}; char={e.pos}","valid JSON syntax",True) from None
def write(p,x): p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(pretty(x))
def blob(raw): return hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()
def clean(v): return str(v or "").strip()
def text(v,f):
    s=clean(v)
    if not s: raise VError("MISSING_TEXT",f,v,"non-empty text")
    return s
def truncate_utf8(v,limit=5000):
    s=clean(v); raw=s.encode()
    return s if len(raw)<=limit else raw[:limit].decode("utf-8","ignore").rstrip()
def draft_id(path):
    x=Path(path).stem
    if not DRAFT_RE.fullmatch(x): raise VError("INVALID_DRAFT_ID","draft_id",x,"draft-<8..96 letters/digits/hyphens>.json")
    return x
def instant(v,field="timestamp"):
    try: d=datetime.fromisoformat(str(v).replace("Z","+00:00"))
    except ValueError: raise VError("INVALID_TIMESTAMP",field,v,"RFC3339 timestamp with timezone",False) from None
    if d.tzinfo is None: raise VError("INVALID_TIMESTAMP",field,v,"RFC3339 timestamp with timezone",False)
    return d
def zulu(d): return d.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
def publish_slots(path=PUBLISH_SLOTS):
    x=read(path)
    if not isinstance(x,dict) or set(x)!={"timezone","slots"}: raise VError("INVALID_PUBLISH_SLOT_CONFIG",str(path),type(x).__name__,"object with timezone and slots",False)
    if clean(x.get("timezone"))!="Asia/Singapore": raise VError("INVALID_PUBLISH_SLOT_TIMEZONE","timezone",x.get("timezone"),"Asia/Singapore",False)
    raw=x.get("slots")
    if not isinstance(raw,list) or len(raw)!=24: raise VError("INVALID_PUBLISH_SLOTS","slots",type(raw).__name__ if not isinstance(raw,list) else len(raw),"exactly 24 daily slots",False)
    out=[]
    for index,value in enumerate(raw):
        m=re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)",str(value))
        if not m: raise VError("INVALID_PUBLISH_SLOT",f"slots[{index}]",value,"HH:MM",False)
        slot=(int(m.group(1)),int(m.group(2)))
        if slot[1] not in {0,10,20,30,40,50}: raise VError("INVALID_PUBLISH_SLOT_MINUTE",f"slots[{index}]",value,"minute 00, 10, 20, 30, 40, or 50",False)
        out.append(slot)
    if len(set(out))!=len(out): raise VError("DUPLICATE_PUBLISH_SLOT","slots",raw,"24 unique daily slots",False)
    if out!=sorted(out): raise VError("UNSORTED_PUBLISH_SLOTS","slots",raw,"ascending daily order",False)
    return out

def normalize_gender(v):
    g=clean(v).casefold(); return g if g in {"female","male"} else "female"
def normalize_tone(v):
    t=clean(v).casefold(); return t if t in TONES else "natural"
def voice(g,t):
    if g not in {"female","male"}: raise VError("INVALID_LEAD_GENDER","story.lead_gender",g,"female or male")
    if t not in TONES: raise VError("INVALID_STORY_TONE","story.story_tone",t,"approved tone")
    return ("af_bella" if t in EXPRESSIVE else "af_heart") if g=="female" else ("am_fenrir" if t in EXPRESSIVE else "am_echo")
def estimate(hook,script): return round(len((hook+" "+script).split())/(BASE_WORDS_PER_SEC*TTS_SPEED),2)
def strip_repeated_hook(hook,script):
    h=clean(hook); s=clean(script)
    return s[len(h):].lstrip(" \t\r\n-—–:;,.!?") if h and s[:len(h)].casefold()==h.casefold() else s
def last_sentence(script):
    s=clean(script); parts=[x.strip() for x in re.split(r"(?<=[.!?])\s+",s) if x.strip()]
    return parts[-1] if parts else s
def resolve_payoff(v,script):
    p=clean(v); s=clean(script); return p if p and p.casefold() in s.casefold() else last_sentence(s)
def cue_key(v): return re.sub(r"_+","_",re.sub(r"[^a-z0-9]+","_",v.strip().casefold())).strip("_") if isinstance(v,str) else ""
def resolve_emojis(cues):
    if not isinstance(cues,list) or len(cues)!=4: return list(DEFAULT_EMOJIS)
    mapped=[EMOJI_MAP.get(cue_key(cue)) for cue in cues]
    return mapped if all(mapped) and len(set(mapped))==4 else list(DEFAULT_EMOJIS)

def registry(path=BG):
    x=read(path)
    if not isinstance(x,dict) or set(x)!={"assets"} or not isinstance(x.get("assets"),list): raise VError("INVALID_BACKGROUND_REGISTRY",str(path),type(x).__name__,"root object containing exactly assets[]",False)
    return x
def usable(a):
    if not isinstance(a,dict): return False
    try: d=float(a.get("duration_seconds"))
    except (TypeError,ValueError): return False
    return d>=MIN_BG and all(clean(a.get(k)) for k in ("id","category","source_url","download_url"))
def amap(r): return {str(a["id"]):a for a in r["assets"] if isinstance(a,dict) and isinstance(a.get("id"),str)}
def background_category(a): return clean(a.get("category")) or "satisfying_process"
def category_assets(r):
    out={}; seen=set()
    for a in r["assets"]:
        if not usable(a): continue
        bid=clean(a.get("id"))
        if not bid or bid in seen: continue
        seen.add(bid); out.setdefault(background_category(a),[]).append(a)
    return out
def viable_background_categories(r):
    groups=category_assets(r); return sorted((k for k,v in groups.items() if len(v)>=MIN_CATEGORY_BACKGROUNDS),key=lambda x:(x.casefold(),x))
def resolve_background_category(requested,r):
    groups=category_assets(r); viable={k:v for k,v in groups.items() if len(v)>=MIN_CATEGORY_BACKGROUNDS}
    if not viable: raise VError("NO_USABLE_BACKGROUND","data/backgrounds.json",0,"at least one category with three distinct valid approved backgrounds",False)
    requested=clean(requested); folded=requested.casefold()
    if requested in viable: return requested
    for category in sorted(viable,key=lambda x:(x.casefold(),x)):
        if category.casefold()==folded: return category
    return sorted(viable,key=lambda x:(-len(viable[x]),x.casefold(),x))[0]
def select_background_ids(requested_category,r,seed):
    category=resolve_background_category(requested_category,r); assets=category_assets(r)[category]
    ranked=sorted(assets,key=lambda a:(hashlib.sha256(f"{seed}:{clean(a.get('id'))}".encode()).hexdigest(),clean(a.get("id"))))
    ids=[clean(a.get("id")) for a in ranked[:MIN_CATEGORY_BACKGROUNDS]]
    if len(ids)!=3 or len(set(ids))!=3: raise VError("NO_USABLE_BACKGROUND","data/backgrounds.json",len(set(ids)),"three distinct valid approved backgrounds",False)
    return ids
def load_planner_analytics(path=None):
    path=Path(path or PLANNER_ANALYTICS)
    try:
        raw=path.read_bytes()
        if len(raw)>MAX_PLANNER_ANALYTICS_BYTES: return None
        data=json.loads(raw.decode("utf-8"))
    except (OSError,UnicodeDecodeError,json.JSONDecodeError):
        return None
    allowed={"analytics_version","generated_at","learning","creative_signals","distribution_signals","audience_signals","data_freshness","warnings"}
    if not isinstance(data,dict) or set(data)-allowed: return None
    if data.get("analytics_version")!=3 or not isinstance(data.get("generated_at"),str): return None
    learning=data.get("learning")
    if not isinstance(learning,dict): return None
    if learning.get("stage") not in {"cold_start","early_learning","established"}: return None
    if learning.get("analytics_weight") not in {"low","medium","normal"}: return None
    minimum=learning.get("minimum_pattern_sample")
    if type(minimum) is not int or minimum<1: return None
    for key in ("creative_signals","distribution_signals","audience_signals"):
        if key in data and not isinstance(data[key],dict): return None
    if "warnings" in data and not isinstance(data["warnings"],list): return None
    return data
def build_context():
    h=read(HIST)
    if not isinstance(h,list): raise VError("INVALID_HISTORY","data/history.json",type(h).__name__,"array")
    categories=viable_background_categories(registry())
    if not categories: raise VError("NO_USABLE_BACKGROUND","data/backgrounds.json",0,"at least one viable category",False)
    cards=[{k:str(x.get(k) or "") for k in ("title","premise","conflict","twist","payoff")} for x in h[-RECENT_LIMIT:] if isinstance(x,dict)]
    out={"context_version":CONTEXT_VERSION,"recent_story_cards":cards,"background_categories":categories}
    base_size=len(pretty(out))
    if base_size>MAX_CONTEXT_BYTES: raise VError("CONTEXT_TOO_LARGE","content/context.json",base_size,f"<={MAX_CONTEXT_BYTES} bytes")
    analytics=load_planner_analytics()
    if analytics is not None:
        candidate={**out,"analytics_summary":analytics}
        if len(pretty(candidate))<=MAX_CONTEXT_BYTES: out=candidate
    write(CTX,out); return out

def normalize_winner(w,index):
    if not isinstance(w,dict): raise VError("INVALID_WINNER_FIELDS",f"winners[{index}]",type(w).__name__,"winner object")
    hook=clean(w.get("hook")); script=strip_repeated_hook(hook,w.get("narration")); raw_topic=w.get("trend_topic")
    return {"premise":clean(w.get("premise")),"category":clean(w.get("category")),"conflict":clean(w.get("conflict")),"twist":clean(w.get("twist")),"hook":hook,"hook_type":clean(w.get("hook_type")).casefold(),"narration":script,"title":clean(w.get("title")),"description":truncate_utf8(w.get("description"),5000),"lead_gender":normalize_gender(w.get("lead_gender")),"story_tone":normalize_tone(w.get("story_tone")),"payoff":resolve_payoff(w.get("payoff"),script),"like_cta":clean(w.get("like_cta")),"emoji_cues":w.get("emoji_cues"),"background_category":clean(w.get("background_category")),"trend_aware":w.get("trend_aware"),"trend_topic":raw_topic.strip() if isinstance(raw_topic,str) else raw_topic}
def declared_winner_count(x,required=True):
    if "winner_count" not in x:
        if required: raise VError("MISSING_WINNER_COUNT","winner_count",None,"positive integer matching the caller-provided winner_count",False)
        return None
    count=x.get("winner_count")
    if type(count) is not int or count<1: raise VError("INVALID_WINNER_COUNT","winner_count",count,"positive integer",False)
    return count

def materialize_draft(x,seen=None,require_winner_count=True):
    if not isinstance(x,dict): raise VError("INVALID_DRAFT_ROOT","$",type(x).__name__,"object")
    if "winner" in x: raise VError("LEGACY_DRAFT_SHAPE","winner","present","use winners[] only",False)
    supersedes=x.get("supersedes_draft_id")
    if supersedes is not None and not DRAFT_RE.fullmatch(str(supersedes)): raise VError("INVALID_SUPERSEDES_DRAFT_ID","supersedes_draft_id",supersedes,"valid prior draft id")
    count=declared_winner_count(x,require_winner_count)
    if supersedes and "winners" in x and "replacements" not in x:
        winners=x.get("winners")
        if not isinstance(winners,list) or not winners: raise VError("INVALID_WINNERS","winners",type(winners).__name__ if not isinstance(winners,list) else len(winners),"non-empty winners array")
        source_path=DRAFTS/(supersedes+".json")
        if not source_path.exists(): raise VError("SUPERSEDED_DRAFT_NOT_FOUND","supersedes_draft_id",supersedes,"existing immutable draft",False)
        source_raw=read_draft(source_path)
        source_count=declared_winner_count(source_raw,False)
        if source_count is None:
            source_winners=source_raw.get("winners")
            source_count=len(source_winners) if isinstance(source_winners,list) else None
        if source_count is None: raise VError("SOURCE_WINNER_COUNT_UNRESOLVED","supersedes_draft_id",supersedes,"superseded draft with resolvable winner count",False)
        if count is None: count=source_count
        if count!=source_count: raise VError("WINNER_COUNT_CHANGED","winner_count",count,source_count,False)
        failure_path=FAILS/(supersedes+".json")
        if not failure_path.exists(): raise VError("REPAIR_FAILURE_NOT_FOUND","supersedes_draft_id",supersedes,"matching deterministic failure file",False)
        failure=read(failure_path)
        if failure.get("repairable") is not True or failure.get("error_code")!="WINNER_COUNT_MISMATCH":
            raise VError("FULL_BATCH_REPAIR_NOT_ALLOWED","supersedes_draft_id",supersedes,"repairable WINNER_COUNT_MISMATCH failure",False)
        if len(winners)!=count: raise VError("WINNER_COUNT_MISMATCH","winners",len(winners),f"exactly {count} winners",True)
        return {"winner_count":count,"winners":winners}
    if "replacements" not in x:
        winners=x.get("winners")
        if not isinstance(winners,list) or not winners: raise VError("INVALID_WINNERS","winners",type(winners).__name__ if not isinstance(winners,list) else len(winners),"non-empty winners array")
        if count is None: count=len(winners)
        if len(winners)!=count: raise VError("WINNER_COUNT_MISMATCH","winners",len(winners),f"exactly {count} winners",True)
        return {"winner_count":count,"winners":winners}
    if "winners" in x or not supersedes: raise VError("INVALID_REPAIR_SHAPE","$","mixed or missing supersedes","winner_count plus supersedes_draft_id plus replacements[] only")
    replacements=x.get("replacements")
    if not isinstance(replacements,list) or not replacements: raise VError("INVALID_REPLACEMENTS","replacements",replacements,"non-empty replacements array")
    seen=set(seen or ())
    if supersedes in seen: raise VError("REPAIR_CYCLE","supersedes_draft_id",supersedes,"acyclic repair chain",False)
    seen.add(supersedes)
    source_path=DRAFTS/(supersedes+".json")
    if not source_path.exists(): raise VError("SUPERSEDED_DRAFT_NOT_FOUND","supersedes_draft_id",supersedes,"existing immutable draft",False)
    source=materialize_draft(read_draft(source_path),seen,False)
    if count is None: count=source["winner_count"]
    if count!=source["winner_count"]: raise VError("WINNER_COUNT_CHANGED","winner_count",count,source["winner_count"],False)
    winners=list(source["winners"])
    failure_path=FAILS/(supersedes+".json")
    if not failure_path.exists(): raise VError("REPAIR_FAILURE_NOT_FOUND","supersedes_draft_id",supersedes,"matching deterministic failure file",False)
    failure=read(failure_path)
    if failure.get("repairable") is not True: raise VError("REPAIR_NOT_ALLOWED","supersedes_draft_id",supersedes,"repairable deterministic failure",False)
    violations=failure.get("violations") or []
    expected={v.get("winner_index") for v in violations if isinstance(v,dict) and isinstance(v.get("winner_index"),int)}
    supplied=set()
    for n,replacement in enumerate(replacements):
        if not isinstance(replacement,dict) or set(replacement)!={"winner_index","winner"}: raise VError("INVALID_REPLACEMENT",f"replacements[{n}]",replacement,"winner_index and winner")
        index=replacement["winner_index"]
        if not isinstance(index,int) or index<0 or index>=len(winners): raise VError("INVALID_REPLACEMENT_INDEX",f"replacements[{n}].winner_index",index,f"0-{len(winners)-1}")
        if index in supplied: raise VError("DUPLICATE_REPLACEMENT_INDEX","replacements",index,"one replacement per affected winner")
        supplied.add(index); winners[index]=replacement["winner"]
    if expected and supplied!=expected: raise VError("REPAIR_INDEX_MISMATCH","replacements",sorted(supplied),f"exact affected winner indexes {sorted(expected)}")
    if len(winners)!=count: raise VError("WINNER_COUNT_MISMATCH","winners",len(winners),f"exactly {count} winners",False)
    return {"winner_count":count,"winners":winners}

def normalize_draft(x):
    materialized=materialize_draft(x)
    return {"winner_count":materialized["winner_count"],"winners":[normalize_winner(w,i) for i,w in enumerate(materialized["winners"])]}

def collect_draft_violations(d):
    out=[]; required=("premise","category","conflict","twist","hook","narration","title","description")
    for index,w in enumerate(d["winners"]):
        title=clean(w.get("title"))
        for field in required:
            value=clean(w.get(field))
            if not value:
                out.append({"winner_index":index,"winner_title":title,"error_code":"MISSING_TEXT","field":f"winners[{index}].{field}","observed_value":value,"required_constraint":"non-empty text"})
        hook_type=w.get("hook_type")
        if hook_type not in HOOK_TYPES:
            out.append({"winner_index":index,"winner_title":title,"error_code":"INVALID_HOOK_TYPE","field":f"winners[{index}].hook_type","observed_value":hook_type,"required_constraint":"one supported hook type"})
        aware=w.get("trend_aware"); topic=w.get("trend_topic")
        if type(aware) is not bool:
            out.append({"winner_index":index,"winner_title":title,"error_code":"INVALID_TREND_AWARE","field":f"winners[{index}].trend_aware","observed_value":aware,"required_constraint":"boolean true or false"})
        elif aware:
            if not isinstance(topic,str) or not topic.strip():
                out.append({"winner_index":index,"winner_title":title,"error_code":"TREND_TOPIC_REQUIRED","field":f"winners[{index}].trend_topic","observed_value":topic,"required_constraint":"non-empty string when trend_aware=true"})
        elif topic is not None:
            out.append({"winner_index":index,"winner_title":title,"error_code":"TREND_TOPIC_FORBIDDEN","field":f"winners[{index}].trend_topic","observed_value":topic,"required_constraint":"null when trend_aware=false"})
        hook=clean(w.get("hook")); narration=clean(w.get("narration"))
        if hook and narration:
            secs=estimate(hook,narration)
            if secs<MIN_NARR or secs>MAX_NARR:
                out.append({"winner_index":index,"winner_title":title,"error_code":"NARRATION_TOO_SHORT" if secs<MIN_NARR else "NARRATION_TOO_LONG","field":f"winners[{index}].narration","observed_value":f"estimated_seconds={secs}","required_constraint":f"{MIN_NARR:g}-{MAX_NARR:g}s"})
        if title and len(title)>100:
            out.append({"winner_index":index,"winner_title":title,"error_code":"TITLE_TOO_LONG","field":f"winners[{index}].title","observed_value":len(title),"required_constraint":"<=100"})
    return out

def bg_contract(category,r,seed):
    m=amap(r); seg=[]
    for bid in select_background_ids(category,r,seed):
        a=m[bid]; seg.append({"background_id":bid,"segment_start_seconds":0.0,"segment_duration_seconds":round(min(float(a["duration_seconds"]),MAX_SEGMENT),3)})
    return {"mode":"concatenated_fit_to_short","segments":seg}

def _credential(name):
    value=clean(os.environ.get(name))
    if not value: raise VError("YOUTUBE_AUTH_MISSING",name,"missing","configured YouTube OAuth credential",False)
    return value
def youtube_access_token():
    body=urlencode({"client_id":_credential("RUNTIME_AUTH_A"),"client_secret":_credential("RUNTIME_AUTH_B"),"refresh_token":_credential("RUNTIME_AUTH_C"),"grant_type":"refresh_token"}).encode()
    req=Request("https://oauth2.googleapis.com/token",data=body,method="POST",headers={"Content-Type":"application/x-www-form-urlencoded"})
    try:
        with urlopen(req,timeout=30) as response: data=json.load(response)
    except (HTTPError,URLError,TimeoutError) as exc: raise VError("YOUTUBE_AUTH_FAILED","youtube",type(exc).__name__,"successful OAuth refresh",False) from None
    token=clean(data.get("access_token"))
    if not token: raise VError("YOUTUBE_AUTH_FAILED","youtube","missing access_token","successful OAuth refresh",False)
    return token
def youtube_get(path,params,token):
    url="https://www.googleapis.com/youtube/v3/"+path+"?"+urlencode(params)
    req=Request(url,headers={"Authorization":f"Bearer {token}","Accept":"application/json"})
    try:
        with urlopen(req,timeout=30) as response: return json.load(response)
    except (HTTPError,URLError,TimeoutError) as exc: raise VError("YOUTUBE_QUERY_FAILED",path,type(exc).__name__,"successful YouTube API query",False) from None
def youtube_scheduled_slots():
    token=youtube_access_token(); channels=youtube_get("channels",{"part":"id,contentDetails","mine":"true"},token).get("items",[])
    if len(channels)!=1 or channels[0].get("id")!=EXPECTED_YOUTUBE_CHANNEL_ID: raise VError("YOUTUBE_CHANNEL_MISMATCH","youtube.channel",[x.get("id") for x in channels],EXPECTED_YOUTUBE_CHANNEL_ID,False)
    uploads=((channels[0].get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads")
    if not uploads: raise VError("YOUTUBE_UPLOADS_MISSING","youtube.channel",None,"uploads playlist",False)
    ids=[]; page=None
    while len(ids)<YOUTUBE_SCAN_LIMIT:
        params={"part":"contentDetails","playlistId":uploads,"maxResults":50}
        if page: params["pageToken"]=page
        data=youtube_get("playlistItems",params,token); ids += [x.get("contentDetails",{}).get("videoId") for x in data.get("items",[]) if x.get("contentDetails",{}).get("videoId")]; page=data.get("nextPageToken")
        if not page: break
    occupied=set()
    ids=ids[:YOUTUBE_SCAN_LIMIT]
    for start in range(0,len(ids),50):
        data=youtube_get("videos",{"part":"status","id":",".join(ids[start:start+50]),"maxResults":50},token)
        for item in data.get("items",[]):
            raw=(item.get("status") or {}).get("publishAt")
            if raw:
                try: occupied.add(instant(raw,"youtube.status.publishAt").astimezone(timezone.utc).replace(microsecond=0))
                except VError: continue
    return occupied
def request_publish_slots(path=REQS):
    occupied=set()
    for request_path in sorted(Path(path).glob("*.json")):
        try: document=read(request_path)
        except (OSError,json.JSONDecodeError) as exc: raise VError("INVALID_RESERVED_REQUEST",str(request_path),type(exc).__name__,"valid immutable request JSON",False) from None
        items=document.get("items") if isinstance(document,dict) and isinstance(document.get("items"),list) else [document]
        for item in items:
            publication=item.get("publication") if isinstance(item,dict) else None
            raw=publication.get("publish_at") if isinstance(publication,dict) else None
            if raw:
                occupied.add(instant(raw,f"{request_path}.publication.publish_at").astimezone(timezone.utc).replace(microsecond=0))
    return occupied
def allocate_publish_slots(count,now=None,occupied=None):
    if not isinstance(count,int) or count<=0: raise VError("INVALID_SLOT_COUNT","count",count,"positive integer",False)
    now=(now or datetime.now(SGT)).astimezone(SGT); occupied=(youtube_scheduled_slots()|request_publish_slots()) if occupied is None else occupied
    normalized=set()
    for value in occupied:
        d=value if isinstance(value,datetime) else instant(value,"occupied_slot")
        normalized.add(d.astimezone(timezone.utc).replace(microsecond=0))
    slots=publish_slots(); threshold=now+SLOT_BUFFER; out=[]; day=now.date()
    while len(out)<count:
        for hour,minute in slots:
            candidate=datetime(day.year,day.month,day.day,hour,minute,tzinfo=SGT)
            if candidate<threshold: continue
            utc=candidate.astimezone(timezone.utc).replace(microsecond=0)
            if utc in normalized: continue
            out.append(zulu(utc)); normalized.add(utc)
            if len(out)==count: return out
        day+=timedelta(days=1)
    return out

def content_id_for(did,index,w): return "wd-"+hashlib.sha256(canonical({"source_draft_id":did,"winner_index":index,"winner":w})).hexdigest()[:24]
def make_item(did,index,w,r,publish_at):
    cid=content_id_for(did,index,w); g=w["lead_gender"]; t=w["story_tone"]
    story={"category":w["category"],"premise":w["premise"],"conflict":w["conflict"],"twist":w["twist"],"hook":w["hook"],"hook_type":w["hook_type"],"script":w["narration"],"lead_gender":g,"story_tone":t,"punchline":w["payoff"],"card_emojis":resolve_emojis(w.get("emoji_cues")),"trend_aware":w["trend_aware"],"trend_topic":w["trend_topic"]}
    if clean(w.get("like_cta")): story["like_cta"]=clean(w["like_cta"])
    return {"request_version":2,"content_id":cid,"source_draft_id":did,"channel":{"name":"Wacky Dramas","handle":"@WACKYDRAMAS"},"story":story,"narration":{"engine":"kokoro","voice":voice(g,t),"speed":TTS_SPEED},"background":bg_contract(w.get("background_category"),r,cid),"youtube":{"title":w["title"],"description":w["description"],"hashtags":["#WackyDramas","#Shorts"],"tags":["Wacky Dramas","Shorts"],"category_id":"24","made_for_kids":False},"publication":{"mode":"scheduled","publish_at":publish_at},"visibility":"private","render":{"width":1080,"height":1920,"fps":30,"video_codec":"h264","h264_profile":"high","pixel_format":"yuv420p","audio_codec":"aac","audio_sample_rate":48000,"background_music":False}}
def validate_item(x,r=None):
    top={"request_version","content_id","source_draft_id","channel","story","narration","background","youtube","publication","visibility","render"}
    if not isinstance(x,dict) or set(x)!=top: raise VError("INVALID_REQUEST_ITEM_FIELDS","item",sorted(x) if isinstance(x,dict) else type(x).__name__,"exact V2 item fields",False)
    if x["request_version"]!=2 or not CID_RE.fullmatch(str(x["content_id"])): raise VError("INVALID_REQUEST_IDENTITY","item",x.get("content_id"),"request_version=2 and valid content_id",False)
    if not DRAFT_RE.fullmatch(str(x["source_draft_id"])): raise VError("INVALID_SOURCE_DRAFT_ID","source_draft_id",x["source_draft_id"],"valid draft id",False)
    if x["channel"]!={"name":"Wacky Dramas","handle":"@WACKYDRAMAS"}: raise VError("INVALID_CHANNEL","channel",x["channel"],"canonical channel",False)
    s=x["story"]; required_sk={"category","premise","conflict","twist","hook","script","lead_gender","story_tone","punchline","card_emojis"}; optional_sk={"hook_type","trend_aware","trend_topic","like_cta"}
    if not isinstance(s,dict) or not required_sk<=set(s) or set(s)-(required_sk|optional_sk): raise VError("INVALID_STORY_FIELDS","story",s,"required story fields plus optional creative provenance")
    if ("trend_aware" in s) != ("trend_topic" in s): raise VError("INVALID_TREND_FIELDS","story",s,"both trend_aware and trend_topic or neither")
    for k in required_sk-{"card_emojis"}: text(s[k],"story."+k)
    if "hook_type" in s and s["hook_type"] not in HOOK_TYPES: raise VError("INVALID_HOOK_TYPE","story.hook_type",s["hook_type"],"supported hook type",False)
    if "like_cta" in s:
        cta=text(s["like_cta"],"story.like_cta")
        if len(cta)>80 or "\n" in cta or "\r" in cta: raise VError("INVALID_LIKE_CTA","story.like_cta",s["like_cta"],"single line <=80 characters",False)
    if "trend_aware" in s:
        aware=s["trend_aware"]; topic=s["trend_topic"]
        if type(aware) is not bool: raise VError("INVALID_TREND_AWARE","story.trend_aware",aware,"boolean",False)
        if aware and (not isinstance(topic,str) or not topic.strip()): raise VError("TREND_TOPIC_REQUIRED","story.trend_topic",topic,"non-empty string when trend_aware=true",False)
        if not aware and topic is not None: raise VError("TREND_TOPIC_FORBIDDEN","story.trend_topic",topic,"null when trend_aware=false",False)
    if str(s["punchline"]).casefold() not in str(s["script"]).casefold(): raise VError("PUNCHLINE_NOT_IN_SCRIPT","story.punchline",s["punchline"],"exact phrase in script")
    if not isinstance(s["card_emojis"],list) or not 4<=len(s["card_emojis"])<=6: raise VError("INVALID_CARD_EMOJIS","story.card_emojis",s["card_emojis"],"4-6 entries")
    v=voice(str(s["lead_gender"]),str(s["story_tone"]))
    if x["narration"]!={"engine":"kokoro","voice":v,"speed":TTS_SPEED}: raise VError("INVALID_NARRATION_CONTRACT","narration",x["narration"],f"kokoro/{v}/{TTS_SPEED}",False)
    secs=estimate(str(s["hook"]),str(s["script"]))
    if secs<MIN_NARR or secs>MAX_NARR: raise VError("NARRATION_TOO_SHORT" if secs<MIN_NARR else "NARRATION_TOO_LONG","story.script",f"estimated_seconds={secs}",f"{MIN_NARR:g}-{MAX_NARR:g}s")
    b=x["background"]
    if not isinstance(b,dict) or set(b)!={"mode","segments"} or b["mode"]!="concatenated_fit_to_short": raise VError("INVALID_BACKGROUND_CONTRACT","background",b,"concatenated_fit_to_short segments",False)
    seg=b["segments"]
    if not isinstance(seg,list) or len(seg)!=3: raise VError("INVALID_BACKGROUND_SEGMENTS","background.segments",seg,"3 segments",False)
    ids=[]; m=amap(r) if r else {}
    for n,z in enumerate(seg):
        if not isinstance(z,dict) or set(z)!={"background_id","segment_start_seconds","segment_duration_seconds"}: raise VError("INVALID_BACKGROUND_SEGMENT",f"background.segments[{n}]",z,"id/start/duration",False)
        bid=text(z["background_id"],f"background.segments[{n}].background_id"); ids.append(bid)
        try: start=float(z["segment_start_seconds"]); dur=float(z["segment_duration_seconds"])
        except (TypeError,ValueError): raise VError("INVALID_BACKGROUND_TIMING",f"background.segments[{n}]",z,"numeric timing",False)
        if abs(start)>1e-6 or not MIN_BG<=dur<=MAX_SEGMENT: raise VError("INVALID_BACKGROUND_TIMING",f"background.segments[{n}]",z,f"start=0 duration {MIN_BG:g}-{MAX_SEGMENT:g}",False)
        if r:
            a=m.get(bid)
            if not a or not usable(a): raise VError("BACKGROUND_NOT_ALLOWED","background.segments",bid,"approved promoted asset",False)
            if dur>float(a["duration_seconds"])+.05: raise VError("BACKGROUND_RANGE_EXCEEDS_SOURCE","background.segments",bid,"segment fits source",False)
    if len(set(ids))!=3: raise VError("DUPLICATE_BACKGROUND_ID","background.segments",ids,"3 distinct IDs",False)
    y=x["youtube"]; yk={"title","description","hashtags","tags","category_id","made_for_kids"}
    if not isinstance(y,dict) or set(y)!=yk: raise VError("INVALID_YOUTUBE_FIELDS","youtube",y,"exact YouTube fields",False)
    if len(text(y["title"],"youtube.title"))>100: raise VError("TITLE_TOO_LONG","youtube.title",len(y["title"]),"<=100")
    if len(text(y["description"],"youtube.description").encode())>5000: raise VError("DESCRIPTION_TOO_LONG","youtube.description",len(y["description"].encode()),"<=5000 bytes")
    if not isinstance(y["hashtags"],list) or not isinstance(y["tags"],list) or y["made_for_kids"] is not False: raise VError("INVALID_YOUTUBE_METADATA","youtube",y,"valid arrays and made_for_kids=false",False)
    p=x["publication"]
    if not isinstance(p,dict) or set(p)!={"mode","publish_at"} or p.get("mode")!="scheduled": raise VError("INVALID_PUBLICATION","publication",p,"scheduled publish_at",False)
    d=instant(p.get("publish_at"),"publication.publish_at")
    if d.minute not in {0,10,20,30,40,50} or d.second or d.microsecond: raise VError("INVALID_PUBLICATION_SLOT","publication.publish_at",p.get("publish_at"),"timestamp on minute 00, 10, 20, 30, 40, or 50",False)
    if x["visibility"]!="private": raise VError("INVALID_VISIBILITY","visibility",x["visibility"],"private",False)
    expected={"width":1080,"height":1920,"fps":30,"video_codec":"h264","h264_profile":"high","pixel_format":"yuv420p","audio_codec":"aac","audio_sample_rate":48000,"background_music":False}
    if x["render"]!=expected: raise VError("INVALID_RENDER_CONTRACT","render",x["render"],str(expected),False)
    return x
def request_id_for(did,raw): return "rq-"+hashlib.sha256(canonical({"source_draft_id":did,"draft":raw})).hexdigest()[:24]
def make_batch(did,raw,d,r,slots):
    rid=request_id_for(did,raw)
    items=[make_item(did,i,w,r,slots[i]) for i,w in enumerate(d["winners"])]
    return {"request_version":2,"request_id":rid,"source_draft_id":did,"items":items}
def validate_batch(x,path=None,r=None):
    if not isinstance(x,dict) or set(x)!={"request_version","request_id","source_draft_id","items"}: raise VError("INVALID_BATCH_FIELDS","$",sorted(x) if isinstance(x,dict) else type(x).__name__,"exact V2 batch fields",False)
    if x["request_version"]!=2 or not RID_RE.fullmatch(str(x["request_id"])): raise VError("INVALID_BATCH_IDENTITY","request_id",x.get("request_id"),"request_version=2 and rq- plus 24 hex",False)
    if path and Path(path).name!=x["request_id"]+".json": raise VError("REQUEST_FILENAME_MISMATCH",str(path),Path(path).name,x["request_id"]+".json",False)
    if not DRAFT_RE.fullmatch(str(x["source_draft_id"])): raise VError("INVALID_SOURCE_DRAFT_ID","source_draft_id",x["source_draft_id"],"valid draft id",False)
    items=x["items"]
    if not isinstance(items,list) or not items: raise VError("INVALID_BATCH_ITEMS","items",type(items).__name__ if not isinstance(items,list) else len(items),"non-empty item array",False)
    for item in items:
        validate_item(item,r)
        if item["source_draft_id"]!=x["source_draft_id"]: raise VError("ITEM_DRAFT_MISMATCH","items",item["source_draft_id"],x["source_draft_id"],False)
    cids=[i["content_id"] for i in items]; slots=[i["publication"]["publish_at"] for i in items]
    if len(set(cids))!=len(cids): raise VError("DUPLICATE_CONTENT_ID","items",cids,"unique content IDs",False)
    if len(set(slots))!=len(slots): raise VError("DUPLICATE_BATCH_SLOT","items",slots,"unique slots within this batch",False)
    return x

def fail(did,e,raw=None):
    payload={"draft_id":did,"error_code":e.code,"field":e.field,"observed_value":e.observed,"required_constraint":e.required,"repairable":e.repairable}
    if e.code=="WINNER_COUNT_MISMATCH" and isinstance(raw,dict):
        winners=raw.get("winners")
        if isinstance(winners,list):
            payload["winner_count"]=raw.get("winner_count")
            payload["actual_winner_count"]=len(winners)
            payload["all_winners"]=winners
            payload["affected_winners"]=[{"winner_index":i,"winner":winner} for i,winner in enumerate(winners)]
    if isinstance(e,DraftValidationError):
        payload["violations"]=e.violations
        if isinstance(raw,dict):
            try:
                materialized=materialize_draft(raw)
                indexes=sorted({v.get("winner_index") for v in e.violations if isinstance(v,dict) and isinstance(v.get("winner_index"),int)})
                payload["affected_winners"]=[{"winner_index":i,"winner":materialized["winners"][i]} for i in indexes if 0<=i<len(materialized["winners"])]
            except VError:
                pass
    write(FAILS/(did+".json"),payload)
def preflight_draft(path):
    path=Path(path).resolve(); did=draft_id(path)
    try:
        raw=read_draft(path); materialize_draft(raw)
    except VError as e:
        fail(did,e,raw if "raw" in locals() else None); raise
    return path
def finalize(path):
    path=Path(path).resolve(); did=draft_id(path)
    try:
        raw=read_draft(path); d=normalize_draft(raw); r=registry(); violations=collect_draft_violations(d)
        if violations: raise DraftValidationError(violations)
        target=REQS/(request_id_for(did,raw)+".json")
        if target.exists():
            existing=validate_batch(read(target),target,r)
            slots=[item["publication"]["publish_at"] for item in existing["items"]]
            q=make_batch(did,raw,d,r,slots)
            if target.read_bytes()!=pretty(q): raise VError("IMMUTABLE_REQUEST_CONFLICT",str(target),blob(target.read_bytes()),blob(pretty(q)),False)
            return target
        slots=allocate_publish_slots(len(d["winners"])); q=make_batch(did,raw,d,r,slots); validate_batch(q,target,r)
    except VError as e: fail(did,e,raw if "raw" in locals() else None); raise
    rawq=pretty(q)
    if target.exists() and target.read_bytes()!=rawq: raise VError("IMMUTABLE_REQUEST_CONFLICT",str(target),blob(target.read_bytes()),blob(rawq),False)
    target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(rawq); return target
def validate_file(path):
    path=Path(path); q=validate_batch(read(path),path,registry()); print(f"Batch valid: {path.name}; items={len(q['items'])}; request_version=2"); return q

def make_executions(path,source):
    if not SHA40.fullmatch(source): raise VError("INVALID_SOURCE_SHA","request_source_sha",source,"40 lowercase hex",False)
    path=Path(path); q=validate_batch(read(path),path,registry()); raw=path.read_bytes(); rblob=blob(raw); out=[]
    for item in q["items"]:
        iblob=blob(pretty(item)); cid=item["content_id"]; eid="ex-"+hashlib.sha256(f"{q['request_id']}|{cid}|{rblob}|{iblob}".encode()).hexdigest()[:24]; did="dp-"+hashlib.sha256(eid.encode()).hexdigest()[:20]
        x={"execution_version":2,"execution_id":eid,"request_id":q["request_id"],"content_id":cid,"request_path":f"content/requests/{q['request_id']}.json","request_source_sha":source,"request_blob_sha":rblob,"item_blob_sha":iblob,"contract_hash":CONTRACT_HASH,"dispatch_id":did,"state":"prepared"}
        target=EXECS/(eid+".json"); rawx=pretty(x)
        if target.exists() and target.read_bytes()!=rawx: raise VError("IMMUTABLE_EXECUTION_CONFLICT",str(target),blob(target.read_bytes()),blob(rawx),False)
        target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(rawx); out.append({"execution_id":eid,"content_id":cid,"path":target.relative_to(ROOT).as_posix()})
    return out

def validate_result(x,path=None):
    keys={"result_version","content_id","execution_id","status","youtube_video_id","visibility","verified","publish_at"}
    if not isinstance(x,dict) or set(x)!=keys: raise VError("INVALID_RESULT_FIELDS","$",sorted(x) if isinstance(x,dict) else type(x).__name__,"exact V2 result fields",False)
    if x["result_version"]!=2 or not CID_RE.fullmatch(str(x["content_id"])) or not EID_RE.fullmatch(str(x["execution_id"])): raise VError("INVALID_RESULT_IDENTITY","$",x,"V2 result identity",False)
    if path and Path(path).name!=x["content_id"]+".json": raise VError("RESULT_FILENAME_MISMATCH",str(path),Path(path).name,x["content_id"]+".json",False)
    if x["status"]!="scheduled" or x["visibility"]!="private" or x["verified"] is not True: raise VError("RESULT_NOT_VERIFIED_SCHEDULED","$",x,"scheduled/private/verified",False)
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}",str(x["youtube_video_id"])): raise VError("INVALID_YOUTUBE_VIDEO_ID","youtube_video_id",x["youtube_video_id"],"11 chars",False)
    instant(x["publish_at"],"publish_at"); return x
def ingest(path):
    path=Path(path); x=validate_result(read(path),path); ep=EXECS/(x["execution_id"]+".json")
    if not ep.exists(): raise VError("EXECUTION_NOT_FOUND","execution_id",x["execution_id"],"matching immutable execution",False)
    e=read(ep)
    if e.get("content_id")!=x["content_id"]: raise VError("RESULT_EXECUTION_MISMATCH","content_id",x["content_id"],e.get("content_id"),False)
    rp=ROOT/str(e.get("request_path") or "")
    if not rp.exists(): raise VError("REQUEST_NOT_FOUND","request_path",str(rp),"matching immutable batch request",False)
    q=validate_batch(read(rp),rp,None); matches=[i for i in q["items"] if i["content_id"]==x["content_id"]]
    if len(matches)!=1: raise VError("RESULT_ITEM_UNRESOLVED","content_id",x["content_id"],"exactly one batch item",False)
    item=matches[0]; h=read(HIST)
    if not isinstance(h,list): raise VError("INVALID_HISTORY","data/history.json",type(h).__name__,"array",False)
    if not any(isinstance(i,dict) and i.get("content_id")==x["content_id"] for i in h):
        s=item["story"]; h.append({"content_id":x["content_id"],"title":item["youtube"]["title"],"premise":s["premise"],"category":s["category"],"conflict":s["conflict"],"twist":s["twist"],"payoff":s["punchline"],"publish_at":x["publish_at"]}); write(HIST,h)
    build_context()

def self_test():
    checks=[]
    def ok(name,cond=True):
        if not cond: raise AssertionError(name)
        checks.append(name)
    r=registry(); c=build_context(); groups=category_assets(r)
    ok("1 context compact",len(pretty(c))<=40000); ok("2 viable backgrounds",bool(c["background_categories"]) and all(len(groups.get(x,[]))>=3 for x in c["background_categories"]))
    filler=" ".join(["Then everything changed when the truth finally came out."]*32); payoff="I had the receipts"; bgcat=c["background_categories"][0]
    winner={"premise":"A manager falsely blames an employee.","category":"work","conflict":"The accusation happens in front of the whole team.","twist":"The employee kept screenshots that prove what happened.","hook":"My manager accused me in front of everyone.","hook_type":"accusation","narration":f"My manager accused me in front of everyone. {filler} {payoff}. Nobody could answer after that.","title":"My Manager Picked the Wrong Person to Blame","description":"A workplace accusation turns around fast.","lead_gender":"invalid","story_tone":"invalid","payoff":"missing payoff","emoji_cues":["shock","evidence","panic","victory"],"background_category":bgcat,"trend_aware":False,"trend_topic":None}
    raw={"winner_count":3,"winners":[winner,winner.copy(),winner.copy()]}; d=normalize_draft(raw); ok("3 array accepted",len(d["winners"])==3 and d["winner_count"]==3)
    try: normalize_draft({"winner_count":2,"winners":[winner,winner.copy(),winner.copy()]})
    except VError as e: ok("3a winner count mismatch rejected",e.code=="WINNER_COUNT_MISMATCH" and e.repairable is True)
    else: raise AssertionError("winner count mismatch must fail")
    try: normalize_draft({"winner":winner})
    except VError as e: ok("4 legacy singular rejected",e.code=="LEGACY_DRAFT_SHAPE")
    else: raise AssertionError("legacy draft must fail")
    ok("5 defaults",d["winners"][0]["lead_gender"]=="female" and d["winners"][0]["story_tone"]=="natural")
    ok("6 repeated hook stripped",not d["winners"][0]["narration"].casefold().startswith(d["winners"][0]["hook"].casefold()))
    ok("7 payoff fallback",d["winners"][0]["payoff"]=="Nobody could answer after that.")
    now=datetime(2030,1,1,7,50,tzinfo=SGT); slots=allocate_publish_slots(3,now,occupied=set()); ok("8 exact ten minutes allowed",slots[0]=="2030-01-01T00:00:00Z")
    slots=allocate_publish_slots(2,datetime(2030,1,1,7,50,1,tzinfo=SGT),occupied=set()); ok("9 buffered slot skipped",slots[0]=="2030-01-01T00:20:00Z")
    occupied={datetime(2030,1,1,0,40,tzinfo=timezone.utc)}; slots=allocate_publish_slots(2,datetime(2030,1,1,8,29,tzinfo=SGT),occupied=occupied); ok("10 occupied slot skipped",slots==["2030-01-01T01:00:00Z","2030-01-01T01:20:00Z"])
    slots=allocate_publish_slots(1,datetime(2030,1,1,19,21,tzinfo=SGT),occupied=set()); ok("10a evening rollover",slots[0]=="2030-01-02T00:00:00Z")
    slots=allocate_publish_slots(1,datetime(2030,1,1,23,1,tzinfo=SGT),occupied=set()); ok("10b next-day rollover",slots[0]=="2030-01-02T00:00:00Z")
    test_slots=["2030-01-01T03:00:00Z","2030-01-01T04:00:00Z","2030-01-01T05:00:00Z"]
    batch=make_batch("draft-selftest01",raw,d,r,test_slots); validate_batch(batch,REQS/(batch["request_id"]+".json"),r); ok("11 batch validates",len(batch["items"])==3); ok("12 unique content ids",len({x["content_id"] for x in batch["items"]})==3)
    ok("13 scheduled private",all(x["visibility"]=="private" and x["publication"]["mode"]=="scheduled" for x in batch["items"])); ok("14 contract hash",CONTRACT_HASH=="db118b20737d06509071754851388e51af427b7930cd48708b3e427415fce1de")
    workflows={p.name for p in (ROOT/".github/workflows").glob("*.yml")}; required_workflows={"finalize-draft.yml","backgrounds.yml","dispatch.yml","result.yml","context.yml"}; ok("15 required workflows",required_workflows<=workflows)
    ok("16 planning doc exists",(ROOT/"PLANNING.md").is_file()); ok("17 legacy daily doc removed",not (ROOT/"DAILY.md").exists()); ok("18 legacy adhoc doc removed",not (ROOT/"ADHOC.md").exists())
    source=Path(__file__).read_text(encoding="utf-8"); legacy_mode_key="planning_"+"mode"; ok("19 mode agnostic",legacy_mode_key not in source)
    short=dict(d["winners"][0]); short["narration"]="too short"; violations=collect_draft_violations({"winners":[short,dict(short)]}); ok("20 aggregate draft violations",[v["winner_index"] for v in violations if v["error_code"]=="NARRATION_TOO_SHORT"]==[0,1])
    trend=dict(winner); trend["trend_aware"]=True; trend["trend_topic"]="GTA 6"; trend["hook_type"]="money_stakes"; trend_d=normalize_draft({"winner_count":1,"winners":[trend]}); trend_item=make_item("draft-selftest02",0,trend_d["winners"][0],r,"2030-01-01T03:00:00Z"); validate_item(trend_item,r); ok("21 creative provenance propagated",trend_item["story"]["hook_type"]=="money_stakes" and trend_item["story"]["trend_aware"] is True and trend_item["story"]["trend_topic"]=="GTA 6")
    no_hook=json.loads(json.dumps(trend_item)); no_hook["story"].pop("hook_type"); validate_item(no_hook,r); ok("22 request without hook type remains valid")
    legacy=json.loads(json.dumps(trend_item)); legacy["story"].pop("hook_type"); legacy["story"].pop("trend_aware"); legacy["story"].pop("trend_topic"); validate_item(legacy,r); ok("23 legacy request remains valid")
    bad_hook=dict(winner); bad_hook["hook_type"]="mystery"; violations=collect_draft_violations(normalize_draft({"winner_count":1,"winners":[bad_hook]})); ok("24 invalid hook type rejected",any(v["error_code"]=="INVALID_HOOK_TYPE" for v in violations))
    print(f"SELF_TEST_PASS checks={len(checks)} contract_hash={CONTRACT_HASH}")

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True); sub.add_parser("context"); p=sub.add_parser("preflight-draft"); p.add_argument("--draft",required=True); p=sub.add_parser("finalize"); p.add_argument("--draft",required=True); p=sub.add_parser("validate"); p.add_argument("--request",required=True); p=sub.add_parser("executions"); p.add_argument("--request",required=True); p.add_argument("--request-source-sha",required=True); p=sub.add_parser("ingest-result"); p.add_argument("--result",required=True); sub.add_parser("contract-hash"); sub.add_parser("self-test"); a=ap.parse_args()
    try:
        if a.cmd=="context":
            c=build_context(); print(f"Context rebuilt: recent={len(c['recent_story_cards'])} background_categories={len(c['background_categories'])}")
        elif a.cmd=="preflight-draft": preflight_draft(a.draft); print("Draft JSON valid")
        elif a.cmd=="finalize": print(finalize(a.draft).relative_to(ROOT).as_posix())
        elif a.cmd=="validate": validate_file(a.request)
        elif a.cmd=="executions":
            xs=make_executions(a.request,a.request_source_sha)
            for x in xs: print(x["path"])
            print(json.dumps({"executions":xs},sort_keys=True,separators=(",",":")))
        elif a.cmd=="ingest-result": ingest(a.result); print("Result ingested")
        elif a.cmd=="contract-hash": print(CONTRACT_HASH)
        else: self_test()
    except VError as e:
        print(str(e),file=sys.stderr); raise SystemExit(2)

if __name__=="__main__": main()
