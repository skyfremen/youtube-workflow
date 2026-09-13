"""Deterministic Pexels discovery for long, production-suitable background clips.

Provider/API eligibility only. Schema v2 adds bounded replenishment-session inputs so
ChatGPT can target deficits and exclude already-reviewed provider assets. Schema v1
remains accepted for existing immutable requests.
"""
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus
from media.background_policy import rendition_is_production_suitable
from media.continuous_background import MIN_SEQUENCE_CLIP_SECONDS
from media.pexels_registry_base import api_get, renditions_from_video

DISCOVERY_SCHEMA_VERSION=1
REQUEST_SCHEMA_VERSION=2
DEFAULT_MAX_CANDIDATES=48
MAX_MAX_CANDIDATES=80
SEARCH_PER_PAGE=80
SEARCH_MAX_PAGES=3
MAX_REPLENISH_ATTEMPTS=5
CATEGORY_QUERIES={
 "cooking":("cooking process","cooking food"),"baking":("baking process","bread baking","pastry making"),
 "food_prep":("food preparation","meal prep","cutting vegetables"),"satisfying_process":("satisfying process","oddly satisfying process"),
 "crafting":("craft making","woodworking","pottery making"),"cleaning":("cleaning restoration","pressure washing","deep cleaning","car washing","surface scrubbing","window cleaning","industrial cleaning"),
 "assembly":("industrial assembly","factory assembly","manufacturing process"),"pov_movement":("walking pov","driving pov","train window travel"),
 "city_motion":("city traffic","city walking","urban motion")}
CATEGORY_TARGETS_48={"cooking":6,"baking":5,"food_prep":5,"satisfying_process":6,"crafting":5,"cleaning":6,"assembly":5,"pov_movement":5,"city_motion":5}

def _utc_now(): return datetime.now(timezone.utc).isoformat()

def _load_request(path):
 data=json.loads(Path(path).read_text(encoding="utf-8")); version=data.get("schema_version") if isinstance(data,dict) else None
 base={"schema_version","plan_date","request_id","max_candidates"}
 if version==1:
  if set(data)!=base: raise ValueError("schema-v1 discovery request has invalid fields")
  data={**data,"target_categories":None,"exclude_provider_asset_ids":[],"replenishment_session_id":None,"attempt":1}
 elif version==2:
  expected=base|{"target_categories","exclude_provider_asset_ids","replenishment_session_id","attempt"}
  if set(data)!=expected: raise ValueError("schema-v2 discovery request has invalid fields")
 else: raise ValueError("discovery request schema_version must be 1 or 2")
 if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",str(data["plan_date"])): raise ValueError("plan_date must be YYYY-MM-DD")
 if not re.fullmatch(r"dr-[A-Za-z0-9-]{8,96}",str(data["request_id"])): raise ValueError("request_id must match dr-[A-Za-z0-9-]{8,96}")
 n=data["max_candidates"]
 if isinstance(n,bool) or not isinstance(n,int) or not 1<=n<=MAX_MAX_CANDIDATES: raise ValueError(f"max_candidates must be 1-{MAX_MAX_CANDIDATES}")
 targets=data["target_categories"]
 if targets is not None and (not isinstance(targets,list) or not targets or len(set(targets))!=len(targets) or any(x not in CATEGORY_QUERIES for x in targets)): raise ValueError("target_categories must be null or a unique non-empty list of known categories")
 excluded=data["exclude_provider_asset_ids"]
 if not isinstance(excluded,list) or len(set(map(str,excluded)))!=len(excluded) or any(not str(x).isdigit() for x in excluded): raise ValueError("exclude_provider_asset_ids must contain unique numeric provider IDs")
 attempt=data["attempt"]
 if isinstance(attempt,bool) or not isinstance(attempt,int) or not 1<=attempt<=MAX_REPLENISH_ATTEMPTS: raise ValueError(f"attempt must be 1-{MAX_REPLENISH_ATTEMPTS}")
 sid=data["replenishment_session_id"]
 if version==2 and not re.fullmatch(r"rs-[A-Za-z0-9-]{8,96}",str(sid or "")): raise ValueError("replenishment_session_id must match rs-[A-Za-z0-9-]{8,96}")
 return data

def _eligible_candidate(video,category,query):
 try: duration=float(video.get("duration"))
 except (TypeError,ValueError): return None
 if duration<MIN_SEQUENCE_CLIP_SECONDS:return None
 renditions=renditions_from_video(video); suitable=[x for x in renditions if rendition_is_production_suitable(x)]
 if not suitable:return None
 review=[x for x in renditions if int(x.get("width") or 0)>=360 and int(x.get("height") or 0)>=360] or list(renditions)
 review.sort(key=lambda x:(int(x.get("width") or 0)*int(x.get("height") or 0),float(x.get("fps") or 999),str(x.get("id") or ""))); preview=review[0]
 pid=str(video.get("id") or "").strip(); page=str(video.get("url") or "").strip(); image=str(video.get("image") or "").strip()
 if not pid.isdigit() or not page or not image:return None
 return {"provider_asset_id":pid,"source_page":page,"duration_seconds":duration,"width":int(video.get("width") or 0),"height":int(video.get("height") or 0),"creator":str(video.get("user",{}).get("name") or "Unknown"),"discovery_category":category,"discovery_query":query,"preview_image_url":image,"preview_video_url":str(preview["direct_url"]),"preview_video_width":int(preview["width"]),"preview_video_height":int(preview["height"]),"preview_video_fps":preview.get("fps"),"production_suitable_rendition_count":len(suitable)}

def _category_targets(max_candidates,categories=None):
 categories=list(categories or CATEGORY_QUERIES)
 if categories==list(CATEGORY_QUERIES) and max_candidates==DEFAULT_MAX_CANDIDATES:return dict(CATEGORY_TARGETS_48)
 base,rem=divmod(max_candidates,len(categories)); return {c:base+(1 if i<rem else 0) for i,c in enumerate(categories)}

def discover(max_candidates=DEFAULT_MAX_CANDIDATES,key=None,target_categories=None,exclude_provider_asset_ids=None,attempt=1):
 categories=list(target_categories or CATEGORY_QUERIES); accepted=[]; seen=set(map(str,exclude_provider_asset_ids or [])); diagnostics=[]; targets=_category_targets(max_candidates,categories)
 for category in categories:
  count=0; target=targets[category]
  queries=CATEGORY_QUERIES[category]; offset=(attempt-1)%len(queries); queries=queries[offset:]+queries[:offset]
  for query in queries:
   for page in range(1,SEARCH_MAX_PAGES+1):
    payload=api_get(f"search?query={quote_plus(query)}&per_page={SEARCH_PER_PAGE}&page={page}",key=key); videos=payload.get("videos",[]) if isinstance(payload,dict) else []; new=0
    for video in videos:
     pid=str(video.get("id") or "").strip()
     if not pid or pid in seen:continue
     candidate=_eligible_candidate(video,category,query)
     if not candidate:continue
     seen.add(pid); accepted.append(candidate); count+=1; new+=1
     if count>=target or len(accepted)>=max_candidates:break
    diagnostics.append({"category":category,"target":target,"query":query,"page":page,"returned":len(videos),"new_eligible":new})
    if count>=target or len(accepted)>=max_candidates or not videos:break
   if count>=target or len(accepted)>=max_candidates:break
  if len(accepted)>=max_candidates:break
 return accepted,diagnostics

def build_report(request,key=None):
 candidates,diagnostics=discover(request["max_candidates"],key=key,target_categories=request.get("target_categories"),exclude_provider_asset_ids=request.get("exclude_provider_asset_ids"),attempt=request.get("attempt",1))
 categories=request.get("target_categories") or list(CATEGORY_QUERIES)
 return {"schema_version":DISCOVERY_SCHEMA_VERSION,"request_id":request["request_id"],"plan_date":request["plan_date"],"provider":"Pexels","generated_at":_utc_now(),"replenishment_session_id":request.get("replenishment_session_id"),"attempt":request.get("attempt",1),"excluded_provider_asset_ids":list(map(str,request.get("exclude_provider_asset_ids") or [])),"eligibility":{"minimum_duration_seconds":float(MIN_SEQUENCE_CLIP_SECONDS),"production_rendition_required":True,"visual_review_complete":False,"rule":"API eligibility only; ChatGPT must review preview evidence before verified_preview=true."},"candidate_count":len(candidates),"category_targets":_category_targets(request["max_candidates"],categories),"candidates":candidates,"query_diagnostics":diagnostics}

def main():
 p=argparse.ArgumentParser();p.add_argument("--request",required=True);p.add_argument("--output",required=True);a=p.parse_args();r=build_report(_load_request(a.request));o=Path(a.output);o.parent.mkdir(parents=True,exist_ok=True);o.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8");print(json.dumps({"output":str(o),"candidate_count":r["candidate_count"]},indent=2));raise SystemExit(0 if r["candidate_count"] else 4)
if __name__=="__main__":main()
