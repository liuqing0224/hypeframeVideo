# HyperFrames 专业漫剧批次完成审计

- 审计日期：2026-07-25
- 批次：`ai-little-director-manga-v2`
- 结果：通过
- HyperFrames：`0.7.71`
- 最终批准：`approvals/ai-little-director-manga-v2-studio-preview.json`
- 九镜头成片接触表：`qa/professional-manga-v2-render-contact-sheet.jpg`

## 最终成片

| 视频 | 时长 | 帧数 | 大小 | 最终路径 | SHA-256 |
| --- | ---: | ---: | ---: | --- | --- |
| 广州塔云端小队 | 38.506667 秒 | 1155 | 242,147,499 B | `out/final/guangzhou-tower-cloud-team.mp4` | `e5920f57d03df7489dc47ac79d08ba28b4f3907ed6b24ac60ec00dbababd5f3f` |
| 会发光的太阳系 | 38.506667 秒 | 1155 | 246,023,406 B | `out/final/glowing-solar-system.mp4` | `7e9b6dc1c9c9df04f36c174eedbe93f377a30a676b8ba4f41b1894e828ba72f8` |
| 大航海家的时光信 | 36.501333 秒 | 1095 | 273,331,711 B | `out/final/navigator-time-letter.mp4` | `df4e5f1a2b856cba680e7970450e234957c2327095a7a9ba114621cd31c4d6be` |
| 星种森林 | 38.016000 秒 | 1140 | 261,097,975 B | `out/final/star-seed-forest.mp4` | `5205fb117aa70a3ba8560f309ffcbbbe5169bc4879cd9058551ca21119bf16e8` |

四条最终文件均为 1920x1080、30fps、H.264 视频与 AAC 音频。FFmpeg
完整解码退出码均为 0；FFprobe 的时长、帧数、编码和分辨率与 manifest
一致。

## 专业漫剧升级

- 保留三个叙事场景和资产组，每场编译三个编辑镜头，每条视频共九镜头。
- 每场具有 wide、medium、close 景别变化、两个场内切点和角色微表演。
- 四张任务卡均使用明确的多人脚本、角色音色、逐行停顿、词级时码和短字幕。
- 根 composition 统一持有对白、BGM、环境声及九个镜头 SFX。
- 图层保持 backdrop、rear、architecture、subjects、foreground 独立运动。
- `.motion.json` 记录镜头覆盖、景别、焦点、切点、anticipation 和主体边界。
- 批次批准绑定当前 production manifest、HTML 和 motion sidecar 的 SHA-256，
  旧版批准不能放行本批次。

## 流水线与素材

- 四工程的 `plan`、`visual_generation`、`audio`、`layer_processing`、
  `composition`、`check`、`preview`、`render`、`qa` 阶段均为 `complete`。
- 四个资产清单共包含 36 项已生成 Imagegen 素材；重跑复用现有源素材。
- 每个工程包含 3 个子 composition、3 个 motion sidecar、9 个编辑镜头。
- 媒体全部冻结到本地，渲染期间不访问远程素材。
- 项目包含 7 个有效 skills，其中新增 `direct-professional-manga-video`。
- HyperFrames 从 `0.7.70` 升级到 `0.7.71`，升级后的四工程重新通过严格检查。

## 验收证据

- 项目测试：`10 passed`。
- 7 个项目 skills 均通过 `skill-creator` 的 `quick_validate.py`。
- 四个 `qa/verification.json` 均为 `pass: true`。
- 四个 `qa/render-verification.json` 均为 `pass: true`。
- 四个 `qa/render-manual-review.json` 均为 `pass: true`，并绑定最终
  MP4 SHA-256、九镜头接触表和转场接触表。
- 每条成片均生成 9 个镜头中点、6 个转场边界帧及成片接触表。
- 入场 SFX 均早于或等于主角入场，声音预切为 0–0.30 秒。
- 人工检查未发现黑帧、异常裁切、字幕越界、明显绿边、错误镜像、
  主体比例失衡、前景遮脸或转场残留。

## 本次修复

- 状态恢复现在会根据完整的 Imagegen 队列，把重新编译后错误显示为
  `pending` 的 `visual_generation` 恢复为 `complete`。
- 入场音效 QA 从无方向的固定误差改为有方向的 anticipation lead：
  音效不得晚于主角，最多提前 0.30 秒。
- 批次正式渲染继续限制为两个并发槽。

## 复跑入口

```bash
.venv/bin/python skills/batch-task-card-videos/scripts/pipeline.py summary \
  --batch batches/ai-little-director-cards.json \
  --workspace .

.venv/bin/python -m pytest -q
```
