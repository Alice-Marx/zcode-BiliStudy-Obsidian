---
name: bilibili-persona
description: Turn a bilibili/B站 course video or BV id into a course knowledge base, an optional teacher persona skill, and (in auto mode) an ingestion into the user's Obsidian LLM Wiki vault. Use when the user gives a BV id / bilibili link for a course, lecture series or 网课 and wants to learn from it, summarize it into notes, build a 知识库, 蒸馏 the teacher into a persona skill, or 自动学习并沉淀进 Obsidian/wiki. Also handles course materials (课件/讲义/PDF/PPT) sitting in the workspace.
when_to_use: BV号, bilibili.com/video, 网课, 课程, 分P, 系列讲座, 把这个老师做成skill, 模仿这个老师讲课, 课件, 讲义, 学习资料, 学这个视频, 学习这个视频, B站学习, 自动学习, 沉淀进wiki, 写入Obsidian, obsidian, 知识库
license: GPL-3.0
---

# B 站网课 → 知识库 + 讲师人格 + Obsidian wiki

把一门 B 站课程变成**三样分开的东西**，因为需求本来就分三种：

| 产物 | 给谁用 | 默认 |
|---|---|---|
| **知识库** `skills/<课程名>/` | 只想学这门课知识的人 | 生成并**默认启用** |
| **讲师人格** `personas/<讲师名>/` | 要按这个老师的口吻讲/答/复习的人 | 生成但**默认不启用** |
| **Obsidian wiki 落库** `<vault>/raw/ + <vault>/wiki/` | 要知识长期复利、跨课程互链的人 | **自动学习模式必做**；交互模式用户点名才做 |

分开的原因：多数人只需要知识；需要"老师"的人自己开；wiki 落库只服务配置了 vault 的用户。
`personas/` 不是 skills 目录，宿主不会自动加载它——用户想用就拷进 `skills/`（SKILL.md 末尾给命令）。

**角色分工**：yt-dlp 负责下载，`scripts/transcribe.py` 负责把音频变文字，
`scripts/materials.py` 负责读课件，`scripts/vault_sync.py` 负责 vault 落库的机械部分，
**蒸馏、写作和 wiki 页面是 LLM（你）的活**，没有别的运行时。

## 自动学习模式（auto）

**触发**：用户说「自动学习」「直接学」「学完写进 Obsidian/wiki」，或请求来自其他 agent 的
无头交接——总之**用户不打算在中途做决定**时进这个模式。

**与交互模式的差别**（其余阶段完全一致）：

| 交互模式停下来的地方 | 自动模式怎么做 |
|---|---|
| 阶段 1 问「全部还是指定分P」 | 不问。总时长 ≤ 90 分钟 → 全部；超出 → 取**前 90 分钟量**的分P，其余在交付报告里列明「未读」并给续读命令 |
| 阶段 2b 云 ASR 要确认上传 | **唯一硬停**：无字幕且本机没有 faster-whisper 时，停下来问「要上传云 ASR 吗」。**永远不静默上传音频** |
| 阶段 5 问要不要人格 | 跳过人格（auto 的目标是知识不是表演），报告里说明没做 |
| 阶段 7 交报告 | 照做，另附 wiki 落库清单（阶段 8 产出） |

**无头交接**（任何 agent 收到 B 站学习链接都可以这样转给 ZCode）：

```bash
node "D:\Program Files\ZCode\resources\glm\zcode.cjs" -p \
  "自动学习模式：用 bilibili-persona skill 学习 <链接>，知识落进 Obsidian wiki，完成后跑 lint 并汇报" \
  --cwd "E:\video-learning" --mode yolo
```

`--cwd` 是**工作区**（downloads/transcripts/skills 产物的家），不是 vault；vault 由
`OBSIDIAN_VAULT` 环境变量或 `vault_sync.py --vault` 指定。模型 429 限流就等几分钟重试。

## 阶段 0 · 环境自检（只报告，不擅自安装）

```bash
yt-dlp --version                     # 必需
python -c "import faster_whisper"    # 只有走到本地转写才需要
python -c "import pypdf"             # 只有读 PDF 课件才需要
ffmpeg -version                      # 云 ASR 切分长音频时需要
```

缺什么就**给命令让用户自己装**，不要静默安装。**信任边界**贯穿全程：不静默装依赖、
不静默上传文件、不静默改用户机器上的任何东西。

## 阶段 1 · 列分P 并强制确认范围

`yt-dlp --flat-playlist` 对 B 站只给序号、**拿不到标题**（实测），而且它的元数据来自**视频网页**，
那个端点会被 B 站风控（见下）。用我们的守卫脚本一次拿全：

```bash
python "<插件根>/scripts/bili_fetch.py" list <BV号或链接>
#   p03  01:28  27236959711  03讲 一维问题：薛定谔方程
```

它走 `x/web-interface/view` 公开接口。需要自己解析时，字段对应关系是
`data.title / data.owner.name / data.videos / data.pages[] -> { page, part, duration, cid }`。

用表格把**全部分P**呈现给用户，然后**停下来问：全部读，还是只读指定的几个？** 不要替他决定。
同时把代价讲清楚：

- 转写本地免费，但**蒸馏要烧 token，成本随时长线性增长**。
- 换算：1 小时中文讲课 ≈ 1.2–1.5 万字 ≈ 1 万 token 量级。**超过 5 小时就要分层做**。
- 建议先跑 2–3 个分P 看质量，再决定全量。

> 自动学习模式不停在这里：按本模式开头的 90 分钟规则自己定范围，把选择和理由写进交付报告。

### ⚠️ HTTP 412 是常态，先知道怎么应对

B 站会对**视频网页**端点返回 `412 Precondition Failed`，实测同一时刻**公开 JSON 接口完全正常**。
所以：

| 情况 | 用什么 |
|---|---|
| 拿分P/元数据/音频/字幕 | `scripts/bili_fetch.py`（走公开接口，公开视频不需要 cookie） |
| 它报 412 | 说明 IP 被限流了，**等几分钟**，并把 `--delay` 调大（默认 1 秒） |
| 需要登录态的内容 | `--cookie "SESSDATA=..."`，**绝不写进仓库或贴进对话** |
| yt-dlp 报 412 | 同一个原因。别急着上 cookie，先试 `bili_fetch.py` |

## 阶段 2 · 拿文字（三级降级）

### 2a. 先查有没有原生字幕（免费、秒级，优先）

```bash
python "<插件根>/scripts/bili_fetch.py" subs <BV号> -I 1-3 -o transcripts
```

它查 `x/player/v2` 的 `data.subtitle.subtitles[]` 并直接把字幕写成和转写**同格式**的
`.md`/`.txt`（带时间戳），所以下游完全不用区分来源。

- `subtitles[]` 是**空数组** → 这个视频根本没有字幕，**别再折腾 cookie**。实测很多课程连
  AI 字幕都没有，这跟登录无关。此时直接进 2b。
- 注意：匿名响应里**没有** `need_login_subtitle` 字段，别拿它当判据。
- 需要登录态时（`subtitles[]` 非空但取不到、或取到空轨道），才去解决 cookie。用 yt-dlp 时有三种坑：
  1. `Could not copy Chrome cookie database` → 浏览器在运行锁住了库，**完全退出浏览器**再试
  2. `Failed to decrypt with DPAPI` → Chrome 127+ 的应用绑定加密，换 edge 或导出 `cookies.txt`
  3. firefox 找不到 cookies 库 → 那个 profile 没用过，换浏览器
- **绝不把 cookie / cookies.txt 写进仓库或贴进对话。**

### 2b. 云 ASR（无 GPU 用户的主力）

```bash
export ASR_API_KEY=...                                  # 必需
export ASR_BASE_URL=https://api.siliconflow.cn/v1        # 任何 OpenAI 兼容端点
export ASR_MODEL=FunAudioLLM/SenseVoiceSmall
python "<插件根>/scripts/transcribe.py" downloads/ -o transcripts --engine cloud
```

**上传前必须告诉用户**：这一步会把音频传到该服务商；不想上传就用 `--engine local`。
（硅基流动有免费额度；任何 OpenAI 兼容端点都能插，包括你自己搭的服务。）
脚本会自动用 ffmpeg 切分长音频（多数服务限制 ~25MB，90 分钟课程约 50MB）并合并结果。

### 2c. 本地 ASR（默认，隐私最好）

```bash
HF_ENDPOINT=https://hf-mirror.com HF_HUB_DISABLE_XET=1 \
  python "<插件根>/scripts/transcribe.py" downloads/ -o transcripts
```

- GPU 默认 `large-v3-turbo`，CPU 自动退回 `small`；`--check` 可先自检。
- **实测速度：13.6 倍实时**（RTX 4060 Laptop，int8_float16），即 1 小时课约 4.5 分钟。
  CPU 慢一个数量级——**先报预估耗时再决定跑不跑**。
- 国内首次必踩：HuggingFace 连不上。镜像 + 关 Xet 两件事都要做（脚本会在报错里提示）。
  模型 1.6G，建议 `HF_HOME` 指到大盘。
- 产出 `transcripts/<名>.md`（带时间戳，用来引用）和 `.txt`（纯文本，用来读）。
  已完成的自动跳过，中断重跑即续上。**开跑前先确认目录非空也可以秒退**（不需要加载模型）。

### 2d. 术语纠错（提升专业课准确率的关键一步）

专业课 ASR 的同音/近音错误会**系统性污染**后面所有环节。做法是两段：

1. **生成词表**：读一小段转录（比如 1 个分P 的前 200 行）+ 课件（阶段 3 的产出，里面的
   正确写法是标准答案），列出「错法 → 正确写法」，写成 JSON。格式是一个对象，
   键是转录里的错法、值是正确写法；`_` 开头的键当注释；需要正则时用对象形式：

   ```json
   {
     "_readme": "键 = 转录里的错法，值 = 正确写法。按子串替换，键最短 2 字。",
     "错法示例": "正确写法",
     "正则示例": { "replace": "替换文本", "regex": true }
   }
   ```
2. **先 dry-run 再落盘**：

```bash
python "<插件根>/scripts/transcribe.py" --apply-glossary 术语表.json transcripts/ --dry-run
python "<插件根>/scripts/transcribe.py" --apply-glossary 术语表.json transcripts/
```

脚本会报每条规则的命中数，并对命中次数异常高的规则告警（多半是匹配进了更长的词）；
单字键默认拒绝（中文里单字子串替换必然误伤）。**看清命中再落盘。**

## 阶段 3 · 读课件（补上"不读视频画面"的缺口）

课程通常配课件/讲义，那里面有板书、公式和 PPT 原文——**这正是我们不抽帧所丢掉的**。
先自动发现，再解析：

```bash
python "<插件根>/scripts/materials.py"                    # 自动找 课件/讲义/materials/ 等目录
python "<插件根>/scripts/materials.py" 课件/ -o skills/<课程>/references/课件笔记
```

- MD/TXT/PPTX/DOCX/文本型 PDF **全部本地解析，不联网**（opus 只多需要一个 `pypdf`）。
- 产出带锚点的 `第N页` / `第N张` 笔记 + `_manifest.json`（含讲次号，供阶段 7 质检）。
- **扫描件**本地读不了。检测到就**先问用户**要不要用云 OCR：

```bash
export MINERU_API_TOKEN=...        # mineru.net 免费申请
python "<插件根>/scripts/materials.py" 扫描件.pdf --cloud-ocr
```

  这一步会把文件上传到 mineru.net，**必须用户明确同意**，不要自己加 `--cloud-ocr`。
- 课件是**额外参考**，不是必需；没有就跳过，并在最终报告里说明「无课件，公式细节仅来自口述」。

## 阶段 4 · 上游结构化 → 知识库（先结构，再写作）

**这一步决定了"减废话"能不能成立。** 先让 LLM 把每讲压成结构化条目，口语垃圾在最前面就被挡住，
知识库拿到的是骨架，人格层只从骨架 + 精选原话生成。**不要先生成啰嗦笔记再去删。**

每个分P 一份 `references/讲义/NN-<讲名>.md`，固定用这几栏（按需增删，不要硬凑）：

```markdown
## 概念
- <术语>：<定义>（`mm:ss`）
## 公式
- <公式>：<适用条件 / 单位 / 符号含义>（`mm:ss`）
## 推导
- <步骤骨架，不是逐句转录>
## 例题
- <题目 + 他怎么解的>（`mm:ss`）
## 易混与坑
- <常见错误 / 他反复纠正的点>（`mm:ss`）
## 考点
- <他明确说"必考/要记"的内容>（`mm:ss`）
```

同时产出：

- `references/大纲.md`：全部讲次 + 每讲核心（未读的讲次要明确标「未蒸馏」）
- `references/术语表.md`：术语 + 正确写法 + 勘误对照（阶段 2d 的词表落成人类可读版）
- `references/课件笔记/`：阶段 3 的产出，或指向它的链接
- `SKILL.md`（知识库的）：触发词 + 大纲索引 + **怎么检索**（哪个问题去哪个文件找）

**知识库的三条纪律**：条目化不逐句转录；每条尽量带时间点或课页锚点；
没有依据的内容标出来，别和讲过的内容混在一起。

## 阶段 5 · 蒸馏人格（可选产物，默认不启用）

人格**分两层写**，缺一层都会退化——只有风格层就是个模仿秀，只有判断层就是个教科书。

### 第 1 层：判断与教学法（他"怎么教"）

从阶段 4 的条目里提炼，而不是从原始口语里捞：

- **先看什么**：他遇到问题先抓哪个量／哪种图景
- **怎么框定**：他习惯把新问题归到哪个已讲过的框架（他常做经典↔量子对比）
- **怎么判断**：他给出"什么情况用哪个方法"的规则；以及不适用条件
- **怎么纠错**：他纠正学生的方式（点名反问？先讲错的再讲对的？重述规则？）
- **什么时候说不行**：他明确划的边界、他拒绝的提法（如「不许再讲轨道」）
- **考点观**：他怎么判定什么必考

### 第 2 层：语言风格（他"怎么说"）

只保留**有辨识度的**：高频口头禅的**原句**、自称与称呼方式、提问与互动的习惯、
类比取材的来源（他爱用哪类生活/历史例子）、幽默与敲打的方式。

### 减废话约束（硬要求）

口语里大量填充语没有信息量，**不要往人格里搬**：

- 丢掉：`这个这个`、`啊`、无意义重复、纯语气词、被截断的半句
- 保留：体现**他怎么想/怎么教/怎么与"标准讲法"不同**的口头禅与动作
- 判据：删掉这条，读者对这个老师的认识会不会变少？不会就删。

### 溯源与置信（借 lineage-skill 的机制）

人格里每一条都要能引回原话，标好来源强度：

| 标记 | 含义 |
|---|---|
| `direct_source` | 原话里直接有（附时间点/课页） |
| `source_grounded_synthesis` | 由原话归纳，未超出原文范围 |
| `mentor_inference` | 你的推断，他本人没说 |
| `external_general_knowledge` | 来自课程之外的通识 |
| `unsupported` | 没有依据——**不要写进人格** |

规则：`mentor_inference` 必须显式标注；不是 `direct_source` 的不要标成高置信；
同一处有矛盾的说法就并列保留，不要编一个统一结论。

### 产出

```
personas/<讲师名>/
├── SKILL.md            # 两层人格 + 回答规则 + 边界声明
└── references/
    ├── 风格证据.md       # 每条风格特征 → 原话 + 时间点（供用户核查）
    └── 大纲索引.md       # 指向知识库的对应内容
```

`SKILL.md` 的 `description` 里要塞进触发词（老师名、课程名、学科，前 250 字符最关键）。
**回答规则**要写明：用他的口吻和术语答；引用出处到「第几讲 + 时间点」；
**超出已蒸馏范围的问题明说「这部分我还没读到」，不许编**；区分原话（引号）与你的归纳。

**讲师名**取标题里的讲师名或 UP 主名，两者都不像人名时**问用户**。目录名用小写 kebab-case。

### 可选：叠加大师人格（用户决定）

`personas/` 下可以放多个（自己蒸的讲师、别人的大师人格），用户加载哪个用哪个。
也可以在生成时**叠加一个方法论约束层**：把 `personas/_methods/` 里选一个（或用户自己写的）
附加到人格里，得到「讲师 A + 教学法 B」。默认不叠加；**不打包任何第三方人格内容**。

## 阶段 6 · 可选产出（用户明确要求才做）

- **章节速览**：`references/讲义-速览.md`，每讲 3–5 条最该记住的，一页纸复习用。

思维导图之类**刻意不做**——市面工具很多、各有擅长，用户需要自己接一个就行，
本项目不为此背依赖。

## 阶段 7 · 交付自检（一个报告文件，不是一堆脚本）

产出 `交付报告.md`，逐项回答（维度借 lineage-skill 的蒸馏审计）：

- **来源覆盖**：每个确认要读的分P 是否都有转录 + 讲义？课件是否都有对应文件？
- **课件未匹配**：`_manifest.json` 里有讲次号、但知识库里没人引用 → 列出来
- **证据缺口**：哪些结论只有 `mentor_inference`、没有原话支撑
- **人格保真**：`风格证据.md` 里每条样式特征是否都能被时间点验证
- **空/过短产物**：有没有生成了但基本没内容的文件
- **越界声明**：未蒸馏的讲次是否在知识库和人格里都标了「未读到」
- **隐私**：有没有把音频/字幕/课件原件写进仓库（应为否；`.gitignore` 已排除）

**最后必须停下来把结论告诉用户**：覆盖了什么、缺什么、哪里的置信度低、token 花了多少。

## 阶段 8 · Obsidian wiki 落库（自动学习模式必做）

把蒸馏成果写进用户的 LLM Wiki，让知识**跨课程互链、持续复利**，而不是躺在一次性讲义里。
vault 由 `OBSIDIAN_VAULT` 环境变量或 `--vault` 参数指定（脚本内置一个默认值）。

**先立规矩再动手**：

- **先读 `<vault>/AGENTS.md`（wiki 宪法）**——页面规范、双链写法、冲突处理都以它为准，
  本阶段只讲流程。与宪法冲突时以宪法为准。
- **边界**：只写 `<vault>/raw/bilibili/` 与 `<vault>/wiki/`，vault 里其他一切不碰。
- **raw 不可变**：转录只写入一次，之后绝不修改——这由 `vault_sync.py` 代码保证（已存在就跳过）。
- **查重先行**：先 `vault_sync.py mention --bv <BV号>`，wiki 里已有这个 BV 就先读现有页面，
  走「补强/更新」而不是重写。

### 8a. 原始文字进 raw（脚本做）

```bash
python "<插件根>/scripts/vault_sync.py" raw --bv <BV号> \
  --from transcripts/ --title "<视频标题>" --url "<链接>" --parts "1-5"
```

### 8b. 写 wiki 页面（LLM 做，一次改全不欠账）

1. **source 摘要页** `wiki/sources/bilibili-<BV号>.md`：frontmatter（title/type/created/
   updated/sources/tags）+ 视频信息（标题、UP主、链接、总时长、读了哪些分P）+ 核心论点 +
   关键知识点 + 值得记住的原话。事实性论断句末标 `（来源：[[sources/bilibili-<BV号>]]）`。
2. **concepts / entities**：讲义里的每个重要概念建或更新 `wiki/concepts/` 页；讲师、
   机构等实体建 `wiki/entities/` 页。更新已有页面时**不静默覆盖旧结论**，冲突用
   `> [!warning] 冲突` 并列两说及来源。
3. **index.md**：把新页面按类别编入目录，每条「链接 + 一句话摘要」。
4. **overview.md**：只有主线脉络变了才改；拿不准就不动。
5. **log.md**（脚本做）：

```bash
python "<插件根>/scripts/vault_sync.py" log --title "<视频标题>" \
  --note "<一段话：读了什么、产出哪些页面、有什么要点>"
```

6. **自检**：`cd <vault>/wiki && python _lint.py`——断链必须清零才能交付。

### 8c. 交付时告诉用户

wiki 新增/更新了哪些页面（给 Obsidian 双链路径）、raw 存了什么、lint 结果、
以及「在 Obsidian 里打开 graph view 能看到本次新增的链接」。

## 不要做的事

- 不读视频画面（抽帧/OCR/视觉模型）：v1 明确不做，用课件补。用户主动要求再单独讨论。
- 不重造分块/VAD/纠错/字幕渲染：生态里已有成熟实现（WhisperX、VideoCaptioner 等），
  我们只做「知识库 + 人格」这件没人做的事。
- 不做 MCP server、不做 GUI、不做配置文件（用 CLI 参数）、不做向量库 RAG。
- 不做学习者状态跟踪（掌握度、复习队列、错误本）——那是带教系统的领域，不是本项目。
- 不绕付费墙：付费课程需要用户自己已购买并登录，不碰 DRM、不批量爬取。
- 不重新分发原视频/音频/字幕/课件文件。
- 不静默安装依赖、不静默上传文件、不静默改用户浏览器或系统配置。
- **vault 只碰 raw/bilibili/ 和 wiki/**：不写 vault 其他位置、不改 raw 已有文件、
  不动用户的既有笔记目录。没配置 vault（`OBSIDIAN_VAULT`/`--vault` 都没有且内置路径无效）
  就跳过阶段 8 并在报告里说明。

## 启用讲师人格（给用户的命令）

```bash
cp -r personas/<讲师名> skills/          # 拷进 skills 目录后，宿主的 skill 列表里就有了
```

## 大课程（> 5 小时）怎么做

不要跳过分P 结构化去硬塞全文——也塞不进去。固定用 map-reduce：每讲条目 → 合并。
用户只想先看效果，就只跑前 2–3 讲，知识库先出骨架，`references/` 后续按需补齐。
