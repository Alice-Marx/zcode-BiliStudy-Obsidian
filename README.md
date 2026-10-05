# zcode-BiliStudy-Obsidian（bilibili-persona）

把一门 B 站网课变成**三样东西**：一份能查的课程知识库，一个可选的「讲师人格」，
以及一次**自动落库到 Obsidian LLM Wiki** 的知识沉淀。
三个产物分开，因为需求本来就分三种——多数人只想学知识，需要「老师」的人自己开，
要知识长期复利的人开 wiki 落库。

```
你给一个 BV 号
   ↓  列分P → 确认读哪些（auto 模式按 90 分钟规则自动定）→ 取字幕（没有就本地转写）
   → 读课件 → 每讲结构化 → 蒸馏
skills/<课程>/       知识库：大纲、讲义、术语表、课件笔记     ← 默认启用
personas/<讲师>/     人格：他怎么讲、怎么判断、怎么押考点     ← 默认不启用，要用自己装
<vault>/raw/ + <vault>/wiki/
                     自动学习模式：原始转录进 raw，知识页进 wiki，跨课程互链复利
```

实测：在一门 24 分P 的中文网课上，4 小时 08 分音频本地转写用了 **18 分钟**（13.6 倍实时）。

> **灵感来源**：本项目启发自并扩展自
> [sorrowKnight123/video-to-skill-](https://github.com/sorrowKnight123/video-to-skill-)
> （GPL-3.0），在其「B 站网课 → 知识库 + 讲师人格」管线上新增了 Obsidian LLM Wiki
> 自动落库与自动学习模式。许可与第三方归属见文末。

## 快速开始

```bash
# 1. 依赖（yt-dlp 必需；faster-whisper 只在没字幕时需要）
uv pip install yt-dlp faster-whisper pypdf

# 2. 看看有哪些分P
python scripts/bili_fetch.py list BV1xxxxxxxxx

# 3. 下音频 + 转写（国内先设镜像，见下方「常见问题」）
python scripts/bili_fetch.py audio BV1xxxxxxxxx -I 1-5 -o downloads
python scripts/transcribe.py downloads/ -o transcripts
```

然后在 ZCode 里说：「帮我把这门课做成知识库 `https://www.bilibili.com/video/BV1xxxxxxxxx`」，
或者用命令 `/learn-course BV1xxxxxxxxx 1-5`。

**想全自动**（不停下来确认，学完直接写进 Obsidian wiki）：

```bash
/learn-course https://www.bilibili.com/video/BV1xxxxxxxxx auto
```

或者在 ZCode 里说「**自动学习这个视频并写入 Obsidian**：<链接>」。

## 安装成插件（可选）

ZCode → 设置 → 插件管理 → **发现** → `+` → 添加插件市场，粘贴：

```
https://github.com/Alice-Marx/zcode-BiliStudy-Obsidian
```

装好后 skill 默认启用。不想用市场的话，把 `skills/`、`scripts/`、`personas/_methods/`
拷进你的项目也一样用。

## Obsidian wiki 自动学习

**触发**：请求里带 `auto`，或说「自动学习 / 直接学 / 学完写进 Obsidian / 沉淀进 wiki」。
自动模式不停下来确认（范围按 90 分钟规则自动定、跳过讲师人格），只有一件事永远不会自动做：
**把音频上传到云 ASR 需要你明确同意**。

落库动作（vault 位置由环境变量 `OBSIDIAN_VAULT` 指定，如 `E:\Obsidian_ljw\Obsidian`）：

| 去处 | 内容 | 谁做 |
|---|---|---|
| `<vault>/raw/bilibili/<BV号>/` | 原始转录 + `info.json`（元数据） | `vault_sync.py raw`，**写入一次永不覆盖** |
| `<vault>/wiki/sources/` | 每个视频一份摘要页（核心论点、关键知识、原话） | LLM |
| `<vault>/wiki/concepts/ · entities/` | 新概念建页、已有页面补强；冲突并列标注不覆盖 | LLM |
| `<vault>/wiki/index.md` | 新页面编入目录 | LLM |
| `<vault>/wiki/log.md` | 追加时间线记录 | `vault_sync.py log` |
| 收尾自检 | `cd <vault>/wiki && python _lint.py`，断链清零才算交付 | 脚本 |

**边界**：只写 `raw/bilibili/` 与 `wiki/`，vault 里其他一切不碰；收录前先
`vault_sync.py mention --bv <BV号>` 查重，同一视频重复学习走「补强」不重写。
落库前 LLM 会先读 vault 的 `AGENTS.md`（wiki 宪法）再动手。

## 任何 agent 都能把学习链接转交给 ZCode

这是本项目的典型用法：你的任何一个 agent（Claude Code、Codex、其他 harness）收到
B 站学习视频链接时，不必自己处理，直接无头调用 ZCode：

```bash
node "D:\Program Files\ZCode\resources\glm\zcode.cjs" -p \
  "自动学习模式：用 bilibili-persona skill 学习 <B站链接>，知识落进 Obsidian wiki，完成后跑 lint 并汇报" \
  --cwd "E:\video-learning" --mode yolo
```

- `--cwd` 是**工作区**（下载、转录、课程知识库产物的家），不是 vault；vault 只收
  raw 与 wiki 两处。
- 模型接口 429 限流就等几分钟重试。
- ZCode 里需已安装本插件（`zcode skills list` 应能看到 `bilibili-persona`）。

## 产物长什么样

```
skills/<课程名>/                     # 知识库（默认启用）
├── SKILL.md                        # 触发词 + 大纲索引 + 怎么检索
└── references/
    ├── 大纲.md                      # 全部讲次 + 每讲核心 + 考点清单
    ├── 术语表.md                    # 术语 + 读法 + ASR 勘误对照
    ├── 讲义/01-xxx.md ...           # 每讲一份：概念/公式/推导/例题/易混与坑/考点
    └── 课件笔记/                    # 课件（PDF/PPTX/DOCX）解析结果，带页码锚点

personas/<讲师名>/                    # 人格（默认不启用）
├── SKILL.md                        # 语言风格 + 判断与教学法 + 回答规则
└── references/                     # 原话证据（每条风格特征都能回溯）

<vault>/raw/bilibili/<BV号>/          # 原始转录（info.json 记录元数据）
<vault>/wiki/                         # sources 摘要页 + concepts/entities 互链 + 索引与日志

transcripts/  downloads/             # 原始字幕与音频（已 gitignore，别提交）
```

讲义的六栏是刻意的：**先结构化，再写作**。口语里的填充语在最前面就被挡住，
所以知识库、人格和 wiki 页面都不会被「这个这个」「啊」这类废话污染。

## 主要能力

| 能力 | 说明 |
|---|---|
| **三级降级取文字** | 原生字幕（免费秒出）→ 云 ASR（任何 OpenAI 兼容端点）→ 本地 faster-whisper |
| **自动学习模式** | 不停下来确认：90 分钟规则自动定范围，学完自动落库 wiki、跑 lint、交报告 |
| **Obsidian wiki 落库** | raw 不可变写入、sources/concepts/entities 互链、index/log 登记、BV 查重 |
| **本地转写** | GPU 优先、CPU 自动兜底；`--check` 自检；断点续跑；不需要 torch |
| **术语纠错** | ASR 对专业课术语错得很系统（实测一个词能有五六种错法），用 JSON 词表确定性纠正 |
| **读课件** | PDF/PPTX/DOCX/MD/TXT 本地解析；扫描件可选走云 OCR；补上「不读视频画面」丢的公式 |
| **知识库与人格分离** | 人格生成但默认不启用；还支持叠加教学法（严格推导 / 直觉类比 / 考点导向） |
| **可溯源** | 讲义条目带 `mm:ss`，有人格的带原话证据；缺证据的地方明确标注而不是编 |

## 命令参考

| 命令 | 作用 |
|---|---|
| `bili_fetch.py list <BV>` | 列分P（序号/时长/cid/标题） |
| `bili_fetch.py audio <BV> -I 4-24 -o downloads` | 下音频（串行 + 解码校验） |
| `bili_fetch.py verify <BV> -o downloads` | 校验本地音频是否完整 |
| `bili_fetch.py subs <BV> -I 1-3 -o transcripts` | 把原生字幕存成和转写同格式的 `.md/.txt` |
| `transcribe.py downloads/ -o transcripts` | 转写（`--engine auto\|cloud\|local`） |
| `transcribe.py --check` | 自检设备与模型 |
| `transcribe.py --apply-glossary 词表.json transcripts/ --dry-run` | 术语纠错（先看命中再落盘） |
| `materials.py <课件目录> -o <知识库>/references/课件笔记` | 解析课件 |
| `vault_sync.py paths` | 校验并打印 vault 关键路径 |
| `vault_sync.py raw --bv <BV> --from transcripts/ --title <标题> --url <链接>` | 转录落 raw（写入一次永不覆盖） |
| `vault_sync.py log --title <标题> --note <说明>` | 向 wiki/log.md 追加记录 |
| `vault_sync.py mention --bv <BV>` | 查 wiki 里是否已收录该视频（查重） |
| `mock_asr.py` | 本地假 ASR 服务，无密钥验证云转写链路 |

`bili_fetch.py` 还有个 `--delay`（默认 1 秒，被限流就调大）和 `--workers`（默认 1，
**别调大**，见下方常见问题）。

## 常见问题

### yt-dlp 报 HTTP 412，但接口明明是通的

B 站有两种完全不同的 412：

| 成因 | 表现 | 解法 |
|---|---|---|
| **yt-dlp 走的网页端点被风控** | `yt-dlp -f ba` 每个分P 都 412，而同一时刻 `api.bilibili.com` 的公开接口返回 code 0 | 用 `bili_fetch.py`（直连公开 API） |
| **Python 的 TLS 指纹被 WAF 拒绝** | 同一 URL、同样请求头，`urllib`/`requests` 412，**`curl` 200** | `bili_fetch.py` 会自动改用 curl 重试 |

第二种**跟登录无关，cookie 解决不了**。如果连 curl 也开始 412，那才是 IP 限流：等几分钟，
把 `--delay` 调大。

### 下载下来的音频是坏的，但文件大小看着正常

实测踩过：4 个并发下载时，21 个文件里 12 个的 AAC 帧损坏，**字节数却接近正确**；
而 `ffprobe` 也报完整时长——因为分片 DASH 的 init 段会声明完整时长，媒体数据缺了它也不知道。

所以本项目：**默认串行下载**（`--workers 1`，别调大），下载后**用 ffmpeg 解码校验**
（`ffmpeg -v error -i f -f null -`，0 条错误才算过），失败就重下而不是按字节续传
（分片容器拼接会产生「大小对、内容坏」的文件）。随时可以用 `bili_fetch.py verify` 自查。

### 第一次转写卡在下载模型

HuggingFace 在国内连不上，且它的 Xet 存储后端**没有镜像**，所以两件事都要做：

```bash
export HF_ENDPOINT=https://hf-mirror.com HF_HUB_DISABLE_XET=1
```

```powershell
$env:HF_ENDPOINT='https://hf-mirror.com'; $env:HF_HUB_DISABLE_XET='1'
```

权重 1.6G，建议 `HF_HOME` 指到大盘。脚本在下载失败时会直接把这两行打给你。

### GPU 用不起来

Windows 上只有一件事要保证：**`cublas64_12.dll` 能被找到**。

- CTranslate2 4.5+ 的官方 Windows 轮子**默认不再链接 cuDNN**，网上「必须装 cuDNN 9」的说法
  对当前版本不成立。
- 报 `Library cublas64_12.dll is not found or cannot be loaded` 时，把 CUDA 的 `bin`
  （或 `nvidia-cublas-cu12` 的 `bin`）加进 **PATH**——CT2 用裸 `LoadLibraryA` 加载 cuBLAS，
  `os.add_dll_directory` 对它无效。
- 8G 显存用 `int8_float16`，别用 `float16`。
- 没 GPU 会自动退回 CPU（换 `small` 模型），慢一个数量级。

### 云转写报 404 或返回 HTML

说明 `ASR_BASE_URL` 指向的是**对话模型**网关，它没有 `/audio/transcriptions`。
换一个真正做语音转写的 OpenAI 兼容服务（如硅基流动 `https://api.siliconflow.cn/v1`，
模型 `FunAudioLLM/SenseVoiceSmall`），或者用 `--engine local` 在本机转。

想在没有密钥的情况下验证云链路，跑 `python scripts/mock_asr.py`，再按它输出的提示调用。

### 需要登录态的内容取不到

用 `--cookie "SESSDATA=..."`。yt-dlp 侧还有三种 cookie 坑：浏览器在运行会锁住 cookie 库
（完全退出浏览器再试）、Chrome 127+ 的应用绑定加密解不开（换 edge 或导出 `cookies.txt`）、
firefox 那个 profile 从没用过。

**cookie 属于账号凭据，不要写进仓库、不要贴进对话。**

### wiki 落库报 vault 校验失败

`vault_sync.py` 要求目标目录长得像一个 LLM Wiki vault（有 `wiki/index.md`、`wiki/log.md`、
`AGENTS.md`）。用 `--vault <路径>` 或环境变量 `OBSIDIAN_VAULT` 指向正确的 vault；
都不设则用内置默认路径。

## 依赖

| 依赖 | 什么时候需要 | 安装 |
|---|---|---|
| `yt-dlp` | 可选（`bili_fetch.py` 是主路径，yt-dlp 是备选） | `uv pip install yt-dlp` |
| `faster-whisper` | 本地转写（**不需要 torch**） | `uv pip install faster-whisper` |
| `pypdf` | 读 PDF 课件 | `uv pip install pypdf` |
| `ffmpeg` | 云 ASR 切分长音频、解码校验 | 系统包管理器 / gyan.dev 版 |
| `MINERU_API_TOKEN` | 扫描件课件走云 OCR 时 | mineru.net 免费申请 |

PPTX / DOCX / MD / TXT 课件**不需要任何额外依赖**（用标准库解压取文本）。
`vault_sync.py` 用 Python 标准库，零依赖。

skill 只报告缺什么、给出安装命令，**不会替你静默安装**；也不会静默上传你的文件。

## 设计取舍（明确没做的事）

- **不读视频画面**（抽帧/OCR/视觉模型）：明显更慢更贵，用**课件**补这个缺口。
- **不重造轮子**：分块/VAD/纠错/字幕渲染生态里已有成熟实现，我们只做「知识库 + 人格 + wiki 落库」。
- **不做** MCP server、GUI、配置文件（用 CLI 参数和环境变量）、向量库 RAG、思维导图。
- **不做**学习者状态跟踪（掌握度、复习队列、错误本）——那是带教系统的领域。
- **vault 只碰 `raw/bilibili/` 与 `wiki/`**：不写 vault 其他位置，不改 raw 已有文件，
  不动用户既有笔记；wiki 页面的写作规范以 vault 自己的 `AGENTS.md` 为准。
- **只做 B 站**：换平台等真有第二个需求再说。

## 目录结构

```
marketplace.json                       插件市场清单
.zcode-plugin/plugin.json              插件清单
skills/bilibili-persona/SKILL.md       工作流（阶段 0–8）
commands/learn-course.md               /learn-course <BV号或链接> [分P] [auto]
scripts/bili_fetch.py                  列分P / 下音频 / 存原生字幕
scripts/transcribe.py                  转写（云/本地）+ 术语纠错
scripts/materials.py                   课件解析（本地优先，扫描件可走云 OCR）
scripts/vault_sync.py                  Obsidian vault 落库（raw 不可变写入 / log / 查重）
scripts/mock_asr.py                    假 ASR 服务，验证云链路
personas/_methods/                     三个教学法叠加层模板
```

## 灵感来源与许可

**灵感来源**：[sorrowKnight123/video-to-skill-](https://github.com/sorrowKnight123/video-to-skill-)
——本项目在其管线上扩展，感谢原项目沉淀的 B 站取文字经验（412 应对、串行下载校验、
三级降级转写）与「知识库/人格分离」的设计。

**GPL-3.0**（见 `LICENSE`）。复用的第三方代码归属见 `NOTICE`——衍生作品必须同样以 GPL 开源。

只做**个人学习用途**的本地文字化：不重新分发视频、音频、字幕、课件，不绕过付费墙或 DRM，
不批量爬取，需要登录态的课程请使用你自己已购买的账号。

- `downloads/`、`transcripts/`、`.cache/`、`_refs/` 已在 `.gitignore` 排除，**不要提交或上传**。
- 用本工具生成的**知识库、人格与 wiki 页面内容可以自由分发**；原始字幕、音视频、课件不可以。
- 请遵守 B 站用户协议与你所在地区的法律。使用本工具产生的一切后果由使用者自负。
