# Professional Manga Directing Contract

## Story Architecture

Keep the authored `start`, `middle`, and `end` beats intact. Compile each beat into three internal shots:

| Beat | Shot 1 | Shot 2 | Shot 3 |
| --- | --- | --- | --- |
| start | establish the place and ensemble | reveal the task or disruption | close reaction hook |
| middle | show the scale of pressure | perform the collaborative action | isolate the key decision or clue |
| end | perform the decisive action | reveal the emotional payoff | resolve with a wide closing tableau |

The three scenes remain the asset groups. The nine shots control framing, focus, line placement, and editorial rhythm.

## Shot Blocking

Every shot must carry a `blocking` state rather than relying on one fixed scene layout:

- `subjects.primary|secondary|tertiary`: transform-relative `x`, `y`, `scale`,
  and `opacity`;
- `environment.rear|architecture|foreground`: independent parallax `x`, `y`,
  and `scale`;
- `travel`: the role or ensemble that moves during the shot, plus its intended
  displacement.

Use the first shot to establish separated screen zones, the middle shot to
bring collaborating or conflicting roles into a new spatial relationship, and
the final shot to isolate a reaction or rebuild the closing ensemble. Mirror
horizontal offsets when narrative direction changes. A camera crop does not
count as blocking; at least every subject and two environment layers must
change state across a scene's three shots.

## Task-Card Manga Block

Use this shape inside a card:

```json
{
  "manga": {
    "pacing": "cinematic",
    "dialogue_ratio": 0.67,
    "audience_grade": "primary-and-middle-school",
    "voice_cast": {
      "primary": "zh-CN-XiaoyiNeural",
      "secondary": "zh-CN-YunxiNeural",
      "tertiary": "zh-CN-YunyangNeural"
    },
    "must_show": ["story-critical visible event"],
    "avoid": ["unsupported fact or continuity break"],
    "factual_notes": ["fact that must remain accurate"],
    "scene_scripts": {
      "start": [
        {"speaker": "旁白", "role": "narrator", "kind": "narration", "text": "必要的场景与因果。"},
        {"speaker": "主角", "role": "primary", "kind": "dialogue", "text": "推动行动的短句。"}
      ],
      "middle": [
        {"speaker": "旁白", "role": "narrator", "kind": "narration", "text": "困难改变了当前局面。"},
        {"speaker": "伙伴", "role": "secondary", "kind": "dialogue", "text": "我们一起找出办法。"}
      ],
      "end": [
        {"speaker": "旁白", "role": "narrator", "kind": "narration", "text": "行动带来了明确结果。"},
        {"speaker": "主角", "role": "primary", "kind": "dialogue", "text": "我们完成任务了！"}
      ]
    }
  }
}
```

Provide two to four lines for every configured scene. Use only `narration`, `dialogue`, or `thought`. The compiler assigns two lines to the first and last shots, three lines one per shot, and four lines in a 1/2/1 pattern.

## Dialogue Discipline

- Let narration establish only information that the image and dialogue cannot carry.
- Let dialogue expose intention, inference, coordination, conflict, or change.
- Prefer one action per sentence and one emotional turn per line.
- Keep each line at 40 Chinese characters or fewer.
- Do not repeat the same fact in narration and dialogue.
- Do not add a joke, mascot, danger, technology, historical claim, or magical rule absent from the task card.
- Keep captions identical to spoken wording unless a later audio stage explicitly records an approved alternate.

## Character Continuity

Maintain a ledger for every named character or stable visual role:

- identity and age impression;
- hair, face, body proportions, and signature colors;
- costume and carried equipment;
- current prop ownership and condition;
- screen side, facing direction, and eyeline;
- emotional state entering and leaving each shot.

Treat changes as explicit story events. A generated source direction may differ from the planned direction; record the source direction per role and mirror only in composition.

## Pacing

Use relative intent rather than authored final seconds:

- `compact`: rapid information delivery and hard cuts;
- `standard`: balanced action and reaction;
- `cinematic`: broader establishing shots, motivated pauses, and a clear payoff;
- `gentle`: longer reactions and quieter transitions.

Measure real speech before resolving duration. Silent establishing and reaction shots receive visual holds from the audio/composition stage; they must not duplicate the scene's fallback narration.

## Approval Checklist

- The nine shots read clearly without audio.
- Character and environment staging changes across all three shots in each scene.
- Every spoken line has one owner and one shot.
- Every scene changes the situation.
- The middle scene contains a visible decision or collaborative action.
- The ending resolves both the task and the characters' emotional state.
- No asset prompt must infer an unidentified character, costume, prop, or location.
