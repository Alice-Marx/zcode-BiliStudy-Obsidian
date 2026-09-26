# bilibili-persona · B站网课 → 知识库 + 讲师人格

> **EN** — Turn a bilibili course series into **two separate artifacts**: a course knowledge base
> (enabled by default) and an optional teacher-persona skill you can chat with. Reads course
> materials (PDF/PPTX/DOCX) from your workspace too. Subtitles → cloud ASR → local Whisper,
> in that order. 24-part quantum-mechanics course transcribed at 13.6× realtime on an RTX 4060 laptop.

把一门 B 站网课变成**两样分开的东西**，因为需求本来就分两种：

| 产物 | 给谁用 | 默认 |
|---|---|---|
| **课程知识库** `skills/<课程>/` | 只想学这门课的人 | 生成并**默认启用** |
| **讲师人格** `personas/<老师>/` | 要按老师的口吻讲/答/复习的人 | 生成但**默认不启用** |

分开是刻意的：多数人只需要知识；需要「老师」的人自己开一条命令装进来。
人格还可以**叠加教学法**（严格推导派 / 直觉类比派 / 考点导向派），得到「某位老师 + 某种教法」。

**实测**（RTX 4060 Laptop 8G + i7-14650HX，`large-v3-turbo`，量子力学 3 分P）：

| 音频 | 转写耗时 | 速度 |
|---|---|---|
| 4 小时 08 分 | 18 分 11 秒 | **13.6 倍实时** |

即 1 小时课程约 4.5 分钟出字幕。完整输出示例见 [`examples/wang-kejia-qm/`](examples/wang-kejia-qm/)。

## 安装（两步）

1. 打开 ZCode → 设置 → 插件管理 → **发现** 标签 → 点 `+` → 添加插件市场，粘贴本仓库地址：

   ```
   https://github.com/sorrowKnight123/video-to-skill-
   ```

   （本地克隆路径也可以。）
2. 找到 **B站网课讲师人格** 卡片 → 点安装。装好后默认启用。

不想用市场的话，把 `skills/bilibili-persona/`、`scripts/` 和 `personas/_methods/` 拷到项目里也能用。

## 用法

```
帮我把这门课做成知识库 https://www.bilibili.com/video/BV1sUqJYaEpr
```

或者 `/learn-course BV1sUqJYaEpr 1-3`。流程是：

```
列全部分P → 停下来问你读全部还是指定哪几个
  → 查原生字幕 → 有就秒出；没有就云 ASR 或本地转写
  → 生成/应用术语纠错词表（专业课准确率的关键）
  → 读工作区里的课件（额外参考）
  → 每讲结构化 → 知识库（默认启用）
  → 蒸馏人格：判断与教学法 + 语言风格（默认不启用）
  → 交付自检报告
```

**启用讲师人格**：

```bash
cp -r personas/<老师> skills/      # 拷进去，宿主的 skill 列表里就有了
```

## 拿文字的三级降级

| 级别 | 方式 | 成本 | 何时走这条 |
|---|---|---|---|
| 1 | **视频原生字幕**（含 B 站 AI 字幕） | 免费、秒级 | 有字幕就直接用，优先 |
| 2 | **云 ASR**（任何 OpenAI 兼容端点，如硅基流动有免费额度） | 免费额度 / 极低 | 无字幕且本机没 GPU；**上传音频前会先问你** |
| 3 | **本地 faster-whisper** | 免费，只花时间 | 默认；隐私最好 |

```bash
# 列分P（拿标题和 cid，无需登录）
python scripts/bili_fetch.py list BV1sUqJYaEpr

# 级别 1：原生字幕直接写成和转写同格式的 .md/.txt
python scripts/bili_fetch.py subs BV1sUqJYaEpr -I 1-3 -o transcripts

# 下音频（直连公开 API；yt-dlp 被 412 时的兜底）
python scripts/bili_fetch.py audio BV1sUqJYaEpr -I 4-24 -o downloads

# 级别 2：云 ASR
export ASR_API_KEY=...; export ASR_BASE_URL=https://api.siliconflow.cn/v1; export ASR_MODEL=FunAudioLLM/SenseVoiceSmall
python scripts/transcribe.py downloads/ -o transcripts --engine cloud

# 级别 3：本地（默认；--check 先自检设备和模型）
python scripts/transcribe.py --check
python scripts/transcribe.py downloads/ -o transcripts
```

长音频会自动用 ffmpeg 切分（多数云服务限制 ~25MB，90 分钟课程约 50MB）再合并。
已完成的文件自动跳过；**目录里全转完时会秒退**，不会白加载 1.6G 模型。

### ⚠️ HTTP 412 会发生在 yt-dlp 上，但公开 API 照常工作

实测（2026-09-26）：同一个视频，`yt-dlp -f ba` 在**每个分P**上都报
`HTTP Error 412: Precondition Failed`，而同一时刻 `x/web-interface/view`、`x/player/playurl`、
`x/player/v2` **全部返回 code 0**。原因是 yt-dlp 的元数据取自**视频网页**端点，那个端点被风控。

所以**下载和取字幕默认走 `scripts/bili_fetch.py`**（直连公开接口，公开视频不需要 cookie），
yt-dlp 留作备选。如果 `bili_fetch.py` 也开始报 412，那是 IP 被限流了：**等几分钟**，
并把 `--delay` 调大。别急着上 cookie——cookie 解决不了限流，只会让你多一个凭据要保管。

> ⚠️ **实测提醒**：不要假设课程有字幕。本项目的示例课程（量子力学王可嘉）**一个字幕都没有**，
> 连 B 站 AI 字幕都没有——所以本地转写是主力路径，不是备胎。
> 另外匿名响应里**没有** `need_login_subtitle` 字段，别拿它判断。

## 术语纠错（别跳过这步）

本地 ASR 对专业课术语会**系统性出错**，而且会污染后面所有环节。示例课程实测：
「波粒二象性」被识别成 `玻璃二相性`、「薛定谔方程」被识别成 `薛定恶方程`、
「傅里叶变换」有 5 种错法。做法：

1. 读一小段转录 + 课件（课件的写法是标准答案），让 LLM 生成 `术语表.json`
   （格式见 [`examples/wang-kejia-qm/术语表.json`](examples/wang-kejia-qm/术语表.json)，
   `_` 开头的键是注释；对象形式支持正则）
2. **先 dry-run 看命中，再落盘**：

```bash
python scripts/transcribe.py --apply-glossary 术语表.json transcripts/ --dry-run
python scripts/transcribe.py --apply-glossary 术语表.json transcripts/
```

打印每条规则的命中数，**命中次数异常高的会告警**（多半匹配进了更长的词）；
单字键默认拒绝（中文里单字子串替换必然误伤）。

## 读课件（补上「不读视频画面」的缺口）

课程通常配课件/讲义，那里面有板书、公式和 PPT 原文——**这正是我们不抽帧所丢掉的**。

```bash
python scripts/materials.py                                  # 自动找 课件/讲义/materials/ 等
python scripts/materials.py 课件/ -o skills/<课程>/references/课件笔记
```

- MD / TXT / **PPTX** / **DOCX** / 文本型 **PDF** 全部**本地解析，不联网**（只需 `pypdf` 读 PDF）
- 产出带 `第N页` / `第N张` 锚点的笔记 + `_manifest.json`（含讲次号，供质检核对「课件是否都被引用」）
- **扫描件**本地读不了，检测到会提示。要用云 OCR 得先明确同意：

```bash
export MINERU_API_TOKEN=...        # mineru.net 免费申请
python scripts/materials.py 扫描件.pdf --cloud-ocr      # 会上传文件到 mineru.net
```

## 讲师人格：两层 + 叠加

人格**分两层写**，缺一层都会退化——只有风格层是模仿秀，只有判断层是教科书：

- **判断与教学法**（他"怎么教"）：先看什么、怎么框定问题、怎么判断、怎么给纠错台阶、什么时候说不行
- **语言风格**（他"怎么说"）：只保留**有辨识度的**口头禅原句、称呼方式、类比取材习惯

**减废话是硬约束**：口语里的 `这个这个`、`啊`、无意义重复**不往人格里搬**。
判据是「删掉这条，读者对老师的认识会不会变少」。

**每条都要能引回原话**，用证据强度标记（借 lineage-skill 的机制）：
`direct_source`（原话+时间点）/ `source_grounded_synthesis`（由原话归纳）/ `mentor_inference`（你的推断，必须标注）/
`external_general_knowledge` / `unsupported`（**不许写进人格**）。

**叠加教学法**（可选，默认不叠加）：`personas/_methods/` 里有三个模板，把它们的内容追加进人格并**标注来源**，
得到「老师 A + 教学法 B」。`personas/` 下也可以并列放多个人格，加载哪个用哪个。
本项目**不打包任何第三方人格内容**。

## 可选产出（用户明确要求才做）

- **章节速览**：`references/讲义-速览.md`，每讲 3–5 条，一页纸复习用

思维导图之类**刻意不做**——市面工具很多、各有擅长，用户需要自己接一个就行，本项目不为此背依赖。

## 依赖

| 依赖 | 什么时候需要 | 安装 |
|---|---|---|
| `yt-dlp` | **必需**（下载分P/字幕/音频） | `uv pip install yt-dlp` 或 `pip install yt-dlp` |
| `faster-whisper` | 走本地转写时（**不需要 torch**） | `uv pip install faster-whisper` |
| `pypdf` | 读 PDF 课件时 | `uv pip install pypdf` |
| `ffmpeg` | 云 ASR 切分长音频时 | 系统包管理器 / gyan.dev 版 |

skill **只报告缺什么、给出安装命令，不会替你静默安装**。MD/TXT/PPTX/DOCX 课件不需要任何额外依赖。

## 国内网络必知

**1. HuggingFace 连不上 → 首次下载模型失败。** 镜像和关掉 Xet **都要做**（Xet 没有镜像）：

```powershell
$env:HF_ENDPOINT='https://hf-mirror.com'; $env:HF_HUB_DISABLE_XET='1'
```
```bash
export HF_ENDPOINT=https://hf-mirror.com HF_HUB_DISABLE_XET=1
```

脚本在下载失败时会把这两行直接打给你。权重 1.6G，建议 `HF_HOME` 指到大盘。

**2. B 站字幕需要登录态时有三种坑**（按顺序退让）：

| 报错 | 解法 |
|---|---|
| `Could not copy Chrome cookie database` | 浏览器在运行锁住了库 → **完全退出浏览器**再试，或换 firefox |
| `Failed to decrypt with DPAPI` | Chrome 127+ 应用绑定加密 → 换 edge，或用扩展导出 `cookies.txt` |
| 找不到 firefox cookies 库 | 那个 profile 没用过 → 换浏览器或导出 `cookies.txt` |

**绝不把 cookie / `cookies.txt` 写进仓库或贴进对话。**

## GPU 说明

`faster-whisper` 的 GPU 路径在 Windows 上只有一件事要保证：**`cublas64_12.dll` 能被找到**。

- CTranslate2 4.5+ 的官方 Windows 轮子**默认不再链接 cuDNN**（检查过 `ctranslate2.dll`，里面没有
  cudnn 字样）。网上「必须装 cuDNN 9」的说法对当前版本不成立，官方文档那段是过期的。
- 报 `Library cublas64_12.dll is not found or cannot be loaded` 时，把 CUDA 的 `bin` 目录
  （或 `nvidia-cublas-cu12` 的 `bin`）加到 **PATH**。CT2 用裸 `LoadLibraryA` 加载 cuBLAS，
  `os.add_dll_directory` 对它无效。
- 8G 显存用 `int8_float16`，别用 `float16`。
- 没 GPU 也能用：自动退回 `device=cpu, compute_type=int8`（换 `small` 模型），慢一个数量级。

## 关于成本

- **转写**：本地免费，1 小时课程 ≈ 4.5 分钟（GPU）。
- **蒸馏**：这才是花钱的地方。1 小时中文讲课 ≈ 1.2–1.5 万字，30 小时的课 ≈ 40 万字，
  谁也塞不进上下文，必须分层做（每讲结构化 → 合并）。
  **建议先用 2–3 个分P 试水**，看质量再决定全量。

## 设计取舍（明确没做的事）

- **不读视频画面**（抽帧/OCR/视觉模型）：明显更慢更贵，用**课件**补这个缺口。
- **不重造轮子**：分块/VAD/纠错/字幕渲染生态里已有成熟实现（WhisperX、VideoCaptioner 等），
  我们只做「知识库 + 讲师人格」这件没人做的事。
- **不做** MCP server、GUI、配置文件（用 CLI 参数）、向量库 RAG。
- **不做**学习者状态跟踪（掌握度、复习队列、错误本）——那是带教系统的领域。
- **只做 B 站**：换平台等真有第二个需求再说。
- 不做烧录字幕 OCR 和纯视觉路径（那是 lecture-to-notes 的做法，太重）。

## 目录结构

```
marketplace.json                       插件市场清单（source 指向仓库根）
.zcode-plugin/plugin.json              插件清单
skills/bilibili-persona/SKILL.md       工具工作流（阶段 0–7）
commands/learn-course.md               /learn-course <BV号>
scripts/bili_fetch.py                   列分P / 下音频 / 存原生字幕（直连公开 API，兜住 412）
scripts/transcribe.py                  转写（云/本地）+ 术语纠错
scripts/materials.py                   课件发现与解析（本地优先，扫描件走云 OCR）
personas/_methods/                     三个教学法叠加层模板
examples/wang-kejia-qm/                真实产出示例（3 讲，量子力学）
NOTICE                                 第三方代码归属声明
```

## 版权与免责

本项目采用 **GPL-3.0**（见 `LICENSE`），复用的第三方代码归属见 `NOTICE`。
**衍生作品必须同样以 GPL 开源**，不能闭源分发——如果你需要闭源商用，这个许可证不合适。

只做**个人学习用途**的本地文字化：不重新分发视频、音频、字幕、课件文件，不绕过付费墙或 DRM，
不批量爬取，需要登录态的课程请使用你自己已购买的账号。

- `downloads/`、`transcripts/`、`.cache/`、`_refs/` 已在 `.gitignore` 排除，**不要提交或上传**。
- 用本工具生成的**知识库与人格（提炼与摘要）可以自由分发**；原始字幕和音视频不可以。
- cookie 属于你的账号凭据，不要写进仓库、不要贴到对话里。
- 请遵守 B 站用户协议与你所在地区的法律。使用本工具产生的一切后果由使用者自负。
