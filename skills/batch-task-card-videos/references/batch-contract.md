# Batch Contract

The batch JSON is validated by `assets/task-card-batch.schema.json`.

- IDs use lowercase kebab-case and are unique.
- Every card has exactly three beats and three ordered `shot_hints`.
- Author name and class are production metadata only and never become on-screen text.
- Duration is intentionally absent. Real narration determines final scene durations.
- Defaults are 1920x1080, 30 fps, and an audio provider configuration.

Each card compiles to `videos/<card-id>/`. Cross-stage paths are relative to that directory.
