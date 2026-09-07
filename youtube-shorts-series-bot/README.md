# Wacky Insights Series Shorts Experiment

This folder is an isolated clone of `youtube-shorts-bot` for testing recurring multi-part Shorts and subscriber-focused CTAs.

## Isolation guarantee

- Existing `youtube-shorts-bot` files are not modified by this experiment.
- Existing production GitHub Actions still target `youtube-shorts-bot` only.
- No automatic publish workflow is enabled for this folder.
- Plans, media cache, archive state and analytics in this folder are separate copies.

## Experiment behavior

The planner targets 12-16 of 24 daily Shorts as genuine multi-part series and keeps 8-12 standalone Shorts as controls.

Non-final series parts use dynamic CTAs such as:

- `FOLLOW FOR PART 2`
- `FOLLOW FOR PART 3`

Final parts use `FOLLOW FOR MORE` or `DOUBLE TAP TO AGREE`. Standalone controls keep `DOUBLE TAP TO AGREE`.

Every series Short still requires its own complete setup and punchline. The next-part CTA cannot be used unless the next part exists in the same plan.

## Series plan metadata

Series items add:

- `series_role`
- `series_id`
- `series_title`
- `part_number`
- `part_total`
- `next_part_slot`
- `series_potential`

## Validation

Run both validators for a plan date:

```bash
python youtube-shorts-series-bot/queue_manager.py validate --date YYYY-MM-DD
python youtube-shorts-series-bot/validate_series_plan.py --date YYYY-MM-DD
```

The second validator enforces series continuity, CTA correctness, next-part linkage, spacing, number of series parts, and standalone-control rules.

## Publishing

Do not point the existing production workflows at this folder. Add a separate experiment workflow only after reviewing a generated series plan and deciding to run a live test.
