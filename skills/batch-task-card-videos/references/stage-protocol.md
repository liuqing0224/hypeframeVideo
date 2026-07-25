# Stage Protocol

Stages run in this dependency order:

1. `plan`
2. `visual_generation` and `audio`
3. `layer_processing`
4. `composition`
5. `check`
6. `preview`
7. `render`
8. `qa`

Every stage is `pending`, `ready`, `running`, `complete`, `failed`, or `blocked`.

- Different productions may run concurrently.
- One production has one stage writer.
- Preserve raw Imagegen sources and failed renders.
- Retry only the failed stage and its downstream dependents.
- Checks may run autonomously. Rendering requires explicit final Studio approval.
