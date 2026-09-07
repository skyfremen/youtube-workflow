# Wacky Insights Long-form — Ad-hoc ChatGPT Planning Prompt

Use this file as the entry point for an ad-hoc ChatGPT planning run.

## Task

Create one new Wacky Insights long-form explainer plan for human review only.

Read and follow, in this order:

1. `youtube-longform-bot/planner/PHASE7_PLANNER.md`
2. `youtube-longform-bot/assets/design-system.json`
3. `youtube-longform-bot/assets/registry.json`
4. Recent long-form plan/summary files under `youtube-longform-bot/content/` when useful for avoiding repetition.

If the user supplied a topic, use it. If no topic was supplied, choose one original, broadly relatable everyday explainer topic with a light humorous payoff.

Generate and commit exactly these review artifacts:

- `youtube-longform-bot/content/phase7-plan.json`
- `youtube-longform-bot/content/phase7-summary.txt`

The JSON must contain a complete script, storyboard, visual beats and asset needs. Prefer strong reusable matches from the asset library. When no strong asset exists, describe the required professional reusable asset in `asset_needs[].generation` according to the planner contract.

The JSON approval block must be:

```json
"approval": {
  "status": "review_required",
  "approved_by": null,
  "approved_at": null
}
```

The plain-text summary must make it easy for the user to decide whether the video should be produced. Include title, intended duration, story overview, each scene in plain English, punchline/payoff, reused assets, and new assets expected to be generated.

Do not render the video. Do not trigger GitHub Actions. Do not generate Kokoro narration. Do not modify Shorts files. Stop after committing the JSON and summary, then present the storyline summary to the user and ask for approval to create the video.
