# HyperFrames 像素视频批次完成审计

- 审计日期：2026-07-25
- 批次：`ai-little-director-pixel-v1`
- 结果：通过
- 最终批准：`approvals/ai-little-director-pixel-v1-studio-preview.json`
- 批次接触表：`qa/batch-contact-sheet.jpg`

## 最终成片

| 视频 | 时长 | 帧数 | 编码 | 最终路径 | SHA-256 |
| --- | ---: | ---: | --- | --- | --- |
| 广州塔云端研学小队 | 28.5 秒 | 855 | H.264 + AAC, 1920×1080, 30fps | `out/final/guangzhou-tower-cloud-team.mp4` | `24f23d40abeba3290c02f8e9f45c0c2029973e025869baf3c6ded09853a14f0a` |
| 会发光的太阳系 | 29.5 秒 | 885 | H.264 + AAC, 1920×1080, 30fps | `out/final/glowing-solar-system.mp4` | `0bb0296c8a56b52ae7cbae7d84a16d9caabc5a6afd75f234d047b32a58618cf8` |
| 郑和的时光信 | 29.0 秒 | 870 | H.264 + AAC, 1920×1080, 30fps | `out/final/navigator-time-letter.mp4` | `c24cb5abf91da1021c94e36f1e4ff5a490f292e4e089359e3ffad781b142ec69` |
| 星种森林 | 26.0 秒 | 780 | H.264 + AAC, 1920×1080, 30fps | `out/final/star-seed-forest.mp4` | `2a66aaa8f4a02996c9847610d7d151b1880c4c5ed110ff0de77574cc72465c73` |

四条最终文件均使用 FFmpeg 完整解码视频流和音频流，退出码为 0。FFprobe 检查确认帧数、帧率、分辨率、H.264 视频流和 AAC 音频流均符合声明。

## 流水线与素材

- 四个工程的 `plan`、`visual_generation`、`audio`、`layer_processing`、`composition`、`check`、`preview`、`render`、`qa` 阶段均为 `complete`。
- 四个 `asset-manifest.json` 各包含 9 个 Imagegen 任务，共 36 个；36 个状态均为 `generated`。
- 每个工程包含 3 个子 composition 和 3 个 `.motion.json`。
- 每个工程均包含 `.media/manifest.jsonl` 与 `.media/index.md`，渲染媒体已冻结到本地。
- 每个工程均包含 `BRIEF.md`、`SCRIPT.md`、`STORYBOARD.md`、`frame.md`。
- Edge TTS 使用 `zh-CN-XiaoxiaoNeural`；每条视频包含 3 段旁白和词级时间。
- 全项目排除依赖目录后搜索旧视频引擎名称为零命中，`package.json` 中不存在旧视频引擎依赖。

## 验收证据

- 项目单元测试：`7 passed`。
- 六个项目内 skills 均通过 `skill-creator/scripts/quick_validate.py`。
- `qa/offline-smoke/summary.json`：两个离线工程均为 `pass: true`。
- 四个 `qa/verification.json` 均为 `pass: true`。
- 四个 `qa/render-verification.json` 均为 `pass: true`。
- 四个 `qa/render-manual-review.json` 均为 `pass: true`。
- 四个 `qa/render-contact-sheet.png` 与四个 `qa/render-transition-contact-sheet.png` 均已检查。
- 12 个入场 SFX 与主角入场时间差均在 0.12–0.18 秒，低于 0.25 秒门限。
- 人工检查未发现黑帧、转场遮罩残留、人物裁切、字幕越界、明显绿边、错误遮挡或朝向异常。

## 复跑入口

```bash
.venv/bin/python skills/batch-task-card-videos/scripts/pipeline.py summary \
  --batch batches/ai-little-director-cards.json \
  --workspace .

.venv/bin/pytest -q
```
