# Wacky Dramas Story Rules

## Story goal

Create complete, original first-person dramas with a natural arc:

**card hook → context → escalating conflict → decisive action → consequence/reversal → satisfying payoff**

Good categories include relationship, dating, marriage, betrayal, family, inheritance, money, workplace, revenge, friendship, wedding, entitled-person conflict, neighbours, secrets/discovery, housing/property, parenting, moral dilemmas, kindness, misunderstandings, hidden identity, consequences and believable reversals.

## Originality and safety

- Original stories only.
- Do not copy Reddit posts or closely paraphrase existing stories.
- Do not fabricate wrongdoing about identifiable real people.
- Use broad, natural, conversational English.
- Keep character names minimal unless a name materially improves clarity.
- Every sentence should advance the story.
- Avoid filler, repeated explanations and unnecessary scene-setting.
- Complete the payoff in one Short.
- Never force a Part 2 or create a fake cliffhanger solely for follow bait.
- Prefer a natural consequence, reversal, reveal, boundary or satisfying backfire when it fits.
- The premise must have enough substance to sustain the target duration naturally; never pad a weak idea.

## Semantic punchline contract

The private planner is the semantic authority for every production story. While writing the final script, identify the actual reveal, reversal, comeback, consequence, contradiction, unexpected detail or payoff that delivers the main emotional/comedic/dramatic reward. Do not defer this decision to the renderer or infer it later from audio position, punctuation, keywords, prosody or “last sentence” rules.

Every newly authored schema-v5 `story` contains a required `punchline` object:

```json
{
  "text": "He had deleted the wrong folder.",
  "emphasis_text": "wrong folder",
  "type": "REVERSAL"
}
```

Rules:

- `text` is the complete semantic payoff span and must occur exactly once in `story.script` after safe punctuation/case/apostrophe normalization.
- `emphasis_text` is the strongest payoff wording inside the resolved punchline, normally 1–5 words, and must occur exactly once inside `punchline.text`.
- `type` is optional; when present it must be one of `REVEAL`, `REVERSAL`, `BACKFIRE`, `COMEBACK`, `CONSEQUENCE`, `CONTRADICTION`, or `ABSURDITY`.
- Do not fabricate/paraphrase punchline metadata with words absent from narration.
- The punchline is not automatically the final sentence or clause.
- The punchline must not be the entire story. If no genuine payoff exists, improve/reject the story.
- Repeated wording must remain unambiguous; use enough exact script context to identify the intended payoff.
- Request validation is fail-closed for missing, fabricated, ambiguous or inconsistent semantic metadata.

Wav2Vec2 determines **when** planner-selected words are spoken. The planner determines **which** words carry the payoff. The renderer determines **how** they are styled. Semantic interpretation stays out of the public runtime.

## Opening card and narration sequence

The rendered opening has four phases:

1. Show the opening card for **0.50 seconds of intentional silence** before narration begins.
2. Narrate `story.hook` in full. Do **not** show subtitles during card-title narration.
3. Fade the card out over the renderer transition after the hook completes.
4. Start `story.script` narration and subtitles only after the card is gone.

Planning rules:

- `story.hook` is the spoken opening-card title/headline, not the first story paragraph.
- Prefer roughly **5–10 words** when natural.
- `story.script` must not start by repeating the hook verbatim.
- The first story-body sentence should deepen curiosity immediately through contradiction, discovery, consequence, evidence, urgent conflict or an unanswered event.
- Avoid generic “for context” intros, relationship-history filler, unnecessary ages/family trees or long setup before the interesting event.
- Narrate in first person and keep conflict easy to follow on first listen.
- Use one approved Kokoro voice for the complete Short, resolved from lead gender first and tone second:
  - female natural/general → `af_heart`
  - female expressive/funny/dramatic/sarcastic → `af_bella`
  - male natural/general → `am_echo`
  - male expressive/funny/dramatic/sarcastic → `am_fenrir`
- Under the current contract narration speed remains `1.75` unless current code/config changes it.
- Aim for **120–175 seconds** of the full rendered narration sequence.
- Renderer includes 0.50s opening silence and roughly 0.35s ending silence.
- **178 seconds is the hard production ceiling**; do not trim away the payoff to fit it.

## Title and hook quality

The YouTube title, opening-card hook and first spoken story-body line should cooperate rather than repeat one another.

Titles should create a truthful curiosity gap with specific tension. Prefer concrete contradiction/discovery structures over generic descriptions. Generate materially different truthful title patterns for serious contenders and choose only an accurate title.

Never promise a reveal, person, crime, consequence or emotional event that does not occur in the script.

## Card and YouTube metadata

Each complete production candidate includes:

- 4–6 contextual card emojis;
- a concise spoken hook/headline;
- a truthful YouTube title containing `#Shorts` and no more than 100 characters;
- a short original story-specific description;
- 3–8 relevant visible hashtags, normally including `#Shorts` and `#WackyDramas`;
- 4–12 explicit backend semantic tags without `#`;
- current canonical category and made-for-kids values.

Always use:

- `Wacky Dramas`
- `@WACKYDRAMAS`

Never output retired branding, legacy CTA/series fields, forced Part-2 fields, music requirements or a mutable publication queue.

## Daily ranked-pool planning

`DAILY_PLANNER_PROMPT.md` is the canonical Daily planning contract.

For a normal day ChatGPT creates exactly **36 complete production-quality candidates ranked 1..36**. They are planning candidates, not 36 production requests. `daily-production.yml` mechanically validates them in frozen rank order and promotes the first 24 valid candidates into exactly 24 immutable schema-v5 production requests.

The Daily creative funnel still begins broadly (normally at least 120 distinct premises), rejects weak/duplicate ideas cheaply, develops strong contenders, runs truthful title competition and applies analytics/diversity/editorial reasoning before final rank.

If a candidate fails hard validation, code skips it and uses the next already-ranked reserve; code never repairs or creatively replaces it.

## Ad-hoc ranked-pool planning

`ADHOC_PLANNER_PROMPT.md` is the canonical Ad-hoc contract.

ChatGPT creates exactly **5 complete production-quality candidates ranked 1..5**. `adhoc-production.yml` validates them in frozen rank order and promotes the first valid candidate into one immutable schema-v5 immediate-public request.

Scheduled Ad-hoc and manual/on-demand Ad-hoc identities are explicitly distinguished by the pool contract. Repository code enforces one canonical scheduled Ad-hoc request per Singapore date.

## Background and treatment planning

ChatGPT owns logical background selection, planning-time audit reasoning and treatment decisions. The public runtime does not choose a third logical asset or infer a new treatment.

Use current `media/background_selector.py`, `media/background_treatment.py`, `media/background_policy.py`, `docs/background-media-strategy.md`, registry metadata and private successful receipts as policy/history evidence.

For every candidate:

- primary and backup logical IDs differ;
- both are registered, active, verified, commercially usable, watermark/text-free and sufficiently high quality;
- each has at least one production-suitable rendition after real 9:16 crop rules;
- retention motion and subtitle readability outrank literal story reenactment;
- recent asset/category/segment/playback repetition is avoided when strong alternatives exist;
- both treatments freeze `segment_start_seconds`, `segment_duration_seconds`, and `playback_rate`;
- when source duration is unknown/untrusted, use full-source treatment (`start=0`, `duration=null`) with a valid playback rate;
- the configured emergency pair may be used only after ChatGPT determines the normal pair is not safely eligible and only if the emergency pair still passes hard safety facts.

`media/background_treatment.py` is a policy/history reference and optional planning aid. Its deterministic helper output is **not** the production authority for newly authored ranked pools; ChatGPT freezes the final choice and private validation only accepts/rejects it.

## Schema and immutability

New production candidates use **schema v5**. Schema v4 exists only for recovery/execution of historical immutable requests.

ChatGPT commits ranked planning-pool artifacts, not canonical production requests. Private promotion workflows materialize canonical requests only after validation. Once a pool/request/result/recovery artifact is committed under an append-only path, do not edit or delete it.

Only promoted winners trigger expensive physical media resolution, TTS, alignment, rendering or YouTube upload.
