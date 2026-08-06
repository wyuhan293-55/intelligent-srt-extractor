# 🎬 Intelligent SRT Extractor

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Whisper](https://img.shields.io/badge/ASR-Whisper-orange.svg)](https://github.com/openai/whisper)
[![CodeBuddy](https://img.shields.io/badge/CodeBuddy-Skill-6366f1.svg)](SKILL.md)

**智能视频字幕提取 — 不盲目转录，只处理有信息量的内容**

</div>

---

## 🤔 和普通转录工具有什么不同？

|  | 普通转录 | **Intelligent SRT Extractor** |
|---|---|---|
| 筛选方式 | 全部盲转 | 按文件夹名 / 文件大小 / 拍摄特征智能分类 |
| B-roll | 一律转录（浪费算力 + 产出垃圾 SRT） | **自动识别并跳过** 12+ 类无信息视频 |
| 不确定时 | 直接转录 | **列出候选，让你决定** |
| 专业相机 | 100MB 文件也盲转 | 先检测音频，无声直接跳过 |

---

## ⚡ 快速开始

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/intelligent-srt-extractor.git
cd intelligent-srt-extractor

# 2. 安装 Python 依赖
pip install -r requirements.txt

# 3. 安装 ffmpeg（如未安装）
# Windows:  winget install ffmpeg
# macOS:    brew install ffmpeg
# Linux:    sudo apt install ffmpeg
```

### 四步完成字幕提取

```bash
# 步骤 1：扫描并智能分类
python scripts/scan_and_classify.py "/path/to/video/folder"

# 步骤 2：根据分类结果，确认哪些视频真正需要转录
# （不确定的视频会自动标记为"待确认"）

# 步骤 3：只转录确认的视频
python scripts/transcribe.py "/path/to/video/folder" --model medium

# 步骤 4：术语修正 + 质量检测
python scripts/fix_terms.py "/path/to/video/folder" --fix
```

---

## 🔄 完整工作流

```
                          ┌──────────────────┐
                          │  素材文件夹       │
                          └────────┬─────────┘
                                   │
                          ┌────────▼─────────┐
                          │  scan_and_       │
                          │  classify.py     │
                          └────────┬─────────┘
                                   │
                   ┌───────────────┼───────────────┐
                   │               │               │
            ┌──────▼──────┐ ┌─────▼─────┐ ┌───────▼──────┐
            │  ⏭️ 跳过     │ │ ✅ 转录   │ │  ❓ 不确定    │
            │  B-roll     │ │  面诊     │ │  需用户确认   │
            │  无声自拍   │ │  采访     │ │               │
            │  灰底摆拍   │ │  查房     │ │               │
            └─────────────┘ └─────┬─────┘ └───────┬──────┘
                                  │               │
                          ┌───────▼───────┐       │
                          │  transcribe   │◄──────┘
                          │  .py          │
                          │  (Whisper)    │
                          └───────┬───────┘
                                  │
                          ┌───────▼───────┐
                          │  fix_terms    │
                          │  .py          │
                          │  术语修正     │
                          └───────┬───────┘
                                  │
                          ┌───────▼───────┐
                          │  .srt 文件    │
                          │  同目录同名   │
                          └───────────────┘
```

---

## 📦 目录结构

```
intelligent-srt-extractor/
├── SKILL.md                     # CodeBuddy Skill 定义
├── README.md                    # 本文件
├── LICENSE                      # MIT 开源协议
├── requirements.txt             # Python 依赖
├── .gitignore                   # Git 忽略规则
├── scripts/
│   ├── scan_and_classify.py     # 📊 扫描 + 智能分类
│   ├── transcribe.py            # 🎙️ Whisper 双引擎转录
│   └── fix_terms.py             # 🔧 术语修正 + 质量检测
└── lexicon/
    └── medical_terms.py         # 📖 医美术语词典（可扩展）
```

---

## 🎯 跳过的视频类型（自动识别）

工具会根据文件夹名、文件大小、音频检测自动跳过以下无信息量内容：

| 类型 | 判断依据 | 例子 |
|---|---|---|
| 产品开箱 | 文件夹名含"开箱/拆包" | 假体拆包展示 |
| 自拍氛围 | 文件夹名含"自拍/氛围感" | 患者术前自拍 |
| 灰底摆拍 | 文件夹名含"灰底/grey" | 标准医学摄影 |
| 环境空镜 | 文件夹名含"环境/病床" | 病房环境拍摄 |
| 术后即刻 | 文件夹名含"术后即刻" | 手术刚结束的效果 |
| 无声大文件 | 音频检测 < 1秒 | 专业相机无声录制 |
| 重复短镜头 | 文件 < 3MB | Live Photo / 微信视频 |
| 术中记录 | 文件夹名含"术中/手术" | 无菌手术室环境 |

> 💡 不确定的会标记出来让你确认，不会漏掉重要内容。

---

## 🧩 转录引擎

支持双引擎自动切换：

```bash
# 自动选择（优先 faster-whisper GPU，不可用时回退 openai-whisper CPU）
python scripts/transcribe.py ./videos --engine auto --model medium

# 强制使用 faster-whisper（需要 GPU + CUDA）
python scripts/transcribe.py ./videos --engine faster-whisper --device cuda

# 强制使用 openai-whisper
python scripts/transcribe.py ./videos --engine openai-whisper
```

| 引擎 | 速度 | 显存 | 适用场景 |
|---|---|---|---|
| `faster-whisper` | 3-5x 实时 | 2-4 GB | NVIDIA GPU |
| `openai-whisper` | 1x 实时 | CPU only | 无 GPU / macOS |

---

## 🔧 自定义术语词典

编辑 `lexicon/medical_terms.py`，添加你的领域术语：

```python
TERM_CORRECTIONS = {
    # 格式："Whisper误识别": "正确术语"
    "棚体": "膨体",      # 鼻整形常用
    "下皱壁": "下皱襞",  # 胸部整形
    "提鸡": "提肌",      # 眼部整形
    # ... 添加你的术语
}
```

`fix_terms.py` 会自动遍历所有 SRT 文件，用长匹配优先策略修正这些误识别。

---

## 🖥️ 作为 CodeBuddy Skill 使用

本工具同时也是 CodeBuddy 的一个 Skill，在对话中触发：

> "整理字幕 D:\案例素材\2026.7.13-尹-姐姐"
> "生成字幕 /path/to/videos"
> "转srt /path/to/videos"

触发后自动执行全流程：扫描 → 分类 → 提问 → 转录 → 修正。

---

## 📄 License

MIT — 详见 [LICENSE](LICENSE)
