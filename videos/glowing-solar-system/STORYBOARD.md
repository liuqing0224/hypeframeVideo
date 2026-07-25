---
format: 1920x1080
message: "像一场会发光的博物馆宇宙探险。"
arc: Start -> Challenge -> Resolution
audience: primary-and-middle-school-students
---

director_profile: orbital-repair-countdown
story_engine: 故障逐级扩大，三人按轨道顺序接力修复，亮度与节奏逐镜头累积。
ending_mode: eight-planet-chain-light

## Frame 1 - 熄灭的展厅

- status: animated
- src: compositions/01-start.html
- duration: 13.000s
- transition_in: cut
- scene: 中央悬浮太阳系轨道装置和环形展台；穿橙色连帽外套的中国女孩小曦，抬头看着熄灭的太阳系模型
- performance_lines: 3
- motion: multi-phase-camera, waterfall-entry, sine-wave-loop
- sfx: scene-impact

熄灭的展厅承担故事的 start 节点。

### Shot 1.1 - establish

- framing: wide
- focus: ensemble
- signature: blackout-system
- intent: 交代空间、人物关系和故事目标
- blocking: primary x=-150 y=20 scale=0.84 opacity=1.0; secondary x=-30 y=18 scale=0.86 opacity=1.0; tertiary x=65 y=6 scale=0.82 opacity=1.0
- line: 旁白：中央太阳系模型正在一颗颗熄灭。

### Shot 1.2 - discovery

- framing: medium
- focus: primary
- signature: planet-failure-scan
- intent: 让主角发现异常并推动事件发生
- blocking: primary x=45 y=-24 scale=1.1 opacity=1.0; secondary x=105 y=4 scale=0.78 opacity=1.0; tertiary x=-85 y=14 scale=0.78 opacity=1.0
- line: 小曦：阿朗，你看，行星正在失去亮光！

### Shot 1.3 - reaction

- framing: close
- focus: tertiary
- signature: robot-alert
- intent: 用反应特写建立情绪钩子
- blocking: primary x=125 y=-28 scale=0.78 opacity=1.0; secondary x=-105 y=28 scale=0.78 opacity=1.0; tertiary x=-130 y=-24 scale=1.0 opacity=1.0
- line: 小光：能量连接异常，请帮助我修复轨道。

## Frame 2 - 追逐能量

- status: animated
- src: compositions/02-middle.html
- duration: 14.000s
- transition_in: chromatic-split
- scene: 故障中的控制环、能量核心和透明全息支架；小曦向前奔跑并伸手抓住一块金色能量碎片
- performance_lines: 3
- motion: coordinate-target-zoom, motion-blur-streak, reactive-displacement
- sfx: scene-impact

追逐能量承担故事的 middle 节点。

### Shot 2.1 - pressure

- framing: wide
- focus: ensemble
- signature: fragment-chase
- intent: 展示困难规模和空间压力
- blocking: primary x=-135 y=22 scale=0.86 opacity=1.0; secondary x=-65 y=18 scale=0.86 opacity=1.0; tertiary x=72 y=8 scale=0.82 opacity=1.0
- line: 旁白：三人沿着行星轨道寻找能量碎片。

### Shot 2.2 - action

- framing: medium
- focus: secondary
- signature: orbit-sequence
- intent: 用连续动作呈现解决过程
- blocking: primary x=80 y=-18 scale=0.78 opacity=1.0; secondary x=145 y=-24 scale=1.04 opacity=1.0; tertiary x=-155 y=2 scale=0.78 opacity=1.0
- line: 阿朗：先按顺序连接轨道，别接错位置！

### Shot 2.3 - decision

- framing: close
- focus: primary
- signature: energy-lock
- intent: 锁定关键判断、道具或情绪转折
- blocking: primary x=-72 y=-30 scale=1.12 opacity=1.0; secondary x=92 y=26 scale=0.78 opacity=1.0; tertiary x=82 y=24 scale=0.74 opacity=1.0
- line: 小曦：我去拿金色碎片，小光负责扫描！

## Frame 3 - 点亮未知

- status: animated
- src: compositions/03-end.html
- duration: 11.500s
- transition_in: grid-dissolve
- scene: 恢复运转的金色太阳核心和完整环形轨道；小曦站在中央高举最后一块能量碎片，脸上充满惊喜
- performance_lines: 3
- motion: center-outward-expansion, ambient-glow-bloom, particle-burst
- sfx: scene-impact

点亮未知承担故事的 end 节点。

### Shot 3.1 - climax

- framing: medium
- focus: primary
- signature: core-ignition
- intent: 完成决定性动作并释放高潮
- blocking: primary x=-105 y=-24 scale=1.1 opacity=1.0; secondary x=-90 y=0 scale=0.78 opacity=1.0; tertiary x=100 y=4 scale=0.78 opacity=1.0
- line: 旁白：太阳和八颗行星全部重新发光。

### Shot 3.2 - payoff

- framing: close
- focus: secondary
- signature: planet-chain-light
- intent: 让观众看清结果和人物反应
- blocking: primary x=95 y=-34 scale=0.78 opacity=1.0; secondary x=145 y=-24 scale=1.04 opacity=1.0; tertiary x=-92 y=22 scale=0.76 opacity=1.0
- line: 阿朗：最后一条轨道接通了！

### Shot 3.3 - resolution

- framing: wide
- focus: ensemble
- signature: cosmic-reveal
- intent: 回到环境，给故事留下完整余韵
- blocking: primary x=0 y=14 scale=0.9 opacity=1.0; secondary x=-18 y=12 scale=0.9 opacity=1.0; tertiary x=18 y=10 scale=0.86 opacity=1.0
- line: 小光：好奇心，就是点亮未知的光。
