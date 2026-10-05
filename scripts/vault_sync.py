#!/usr/bin/env python3
"""vault_sync.py — 把学习产物写进 Obsidian LLM Wiki vault（阶段 8 的机械部分）。

分工边界：摘要页、entities/concepts、index.md 条目是 LLM 的活（见 SKILL.md 阶段 8）；
本脚本只做可判定、必须确定性的三件事：
  1. 定位并校验 vault（防止 LLM 猜路径、防止写错目录）
  2. 往 raw/ 落原始转录（写入一次后永不改动——raw 层不可变由代码保证，不靠自觉）
  3. 向 wiki/log.md 追加标准格式条目 + 按 BV 号查重

只写 <vault>/raw/bilibili/ 与 <vault>/wiki/log.md，绝不碰 wiki 其他页面、
绝不碰 vault 里其他任何东西。需要 Python 3.8+，零第三方依赖。

用法：
  python vault_sync.py paths                                  # 校验并打印 vault 结构
  python vault_sync.py raw --bv BV1xxx --from transcripts --title 标题 --url https://...
  python vault_sync.py log --title 某视频 --note 第一段说明 --note 第二段说明
  python vault_sync.py mention --bv BV1xxx                    # 查 wiki 里哪些页面提到过它
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from pathlib import Path

# 默认 vault；环境变量 OBSIDIAN_VAULT 可覆盖，--vault 参数优先级最高。
DEFAULT_VAULT = r"E:\Obsidian_ljw\Obsidian"
RAW_SUBDIR = "raw/bilibili"          # B 站类原始资料在 raw 下的固定去处
TRANSCRIPT_EXTS = {".md", ".txt", ".srt", ".vtt"}


def resolve_vault(cli_value: str | None) -> Path:
    raw = cli_value or os.environ.get("OBSIDIAN_VAULT") or DEFAULT_VAULT
    vault = Path(raw).expanduser().resolve()
    problems = []
    if not vault.is_dir():
        problems.append(f"目录不存在：{vault}")
    else:
        if not (vault / "wiki" / "index.md").is_file():
            problems.append("缺少 wiki/index.md——这不像一个 LLM Wiki vault")
        if not (vault / "wiki" / "log.md").is_file():
            problems.append("缺少 wiki/log.md")
        if not (vault / "AGENTS.md").is_file():
            problems.append("缺少 AGENTS.md（wiki 宪法）——落库前 LLM 必须先读它")
    if problems:
        sys.exit("[vault_sync] vault 校验失败：\n  " + "\n  ".join(problems)
                 + "\n用 --vault <路径> 或环境变量 OBSIDIAN_VAULT 指定正确的 vault。")
    return vault


def _bv_slug(bv: str) -> str:
    bv = bv.strip()
    if not bv:
        sys.exit("[vault_sync] --bv 不能为空")
    for ch in r'\/:*?"<>| ':
        bv = bv.replace(ch, "-")
    return bv


def cmd_paths(args: argparse.Namespace) -> int:
    vault = resolve_vault(args.vault)
    print(f"vault     = {vault}")
    print(f"raw目录   = {vault / RAW_SUBDIR}")
    print(f"log文件   = {vault / 'wiki' / 'log.md'}")
    print(f"宪法      = {vault / 'AGENTS.md'}（阶段 8 动手前 LLM 必须先读）")
    return 0


def cmd_raw(args: argparse.Namespace) -> int:
    vault = resolve_vault(args.vault)
    target = vault / RAW_SUBDIR / _bv_slug(args.bv)
    target.mkdir(parents=True, exist_ok=True)

    copied, skipped = [], []
    for src_dir in args.from_dir or []:
        src = Path(src_dir).expanduser().resolve()
        if not src.is_dir():
            sys.exit(f"[vault_sync] --from 目录不存在：{src}")
        for f in sorted(src.iterdir()):
            if not f.is_file() or f.suffix.lower() not in TRANSCRIPT_EXTS:
                continue
            dest = target / f.name
            if dest.exists():
                skipped.append(f.name)   # raw 不可变：已存在一律跳过，绝不覆盖
                continue
            dest.write_bytes(f.read_bytes())
            copied.append(f.name)

    info_path = target / "info.json"
    if info_path.exists():
        info = json.loads(info_path.read_text(encoding="utf-8"))
        info_msg = "info.json 已存在，保持原样（raw 不可变）"
    else:
        info = {
            "bv": args.bv,
            "url": args.url or "",
            "title": args.title or "",
            "parts": args.parts or "",
            "ingested": _dt.date.today().isoformat(),
            "transcripts": copied,
            "skipped_existing": skipped,
        }
        info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        info_msg = f"info.json 已写入（{len(copied)} 份转录）"

    print(f"raw 落库完成：{target}")
    for name in copied:
        print(f"  + {name}")
    for name in skipped:
        print(f"  = {name}（已存在，跳过——raw 不可变）")
    print(f"  {info_msg}")
    return 0


def cmd_log(args: argparse.Namespace) -> int:
    vault = resolve_vault(args.vault)
    log_path = vault / "wiki" / "log.md"
    date = args.date or _dt.date.today().isoformat()
    lines = [f"\n## [{date}] {args.kind} | {args.title}"]
    for note in args.note or []:
        lines.append(note)
    text = "\n".join(lines) + "\n"
    with open(log_path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"log.md 已追加：{log_path}")
    print(text.rstrip())
    return 0


def cmd_mention(args: argparse.Namespace) -> int:
    vault = resolve_vault(args.vault)
    needle = args.bv.strip()
    hits = []
    wiki = vault / "wiki"
    for root, _dirs, files in os.walk(wiki):
        for name in files:
            if not name.endswith(".md"):
                continue
            p = Path(root) / name
            try:
                if needle in p.read_text(encoding="utf-8"):
                    hits.append(str(p.relative_to(vault)))
            except OSError:
                continue
    if hits:
        print(f"wiki 中已有 {len(hits)} 个页面提到 {needle}（重复收录前先看这些页）：")
        for h in hits:
            print(f"  - {h}")
        return 1
    print(f"wiki 中没有任何页面提到 {needle}，可以收录。")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_vault_arg(p):
        p.add_argument("--vault", help="vault 根目录（默认取 OBSIDIAN_VAULT 环境变量，再退到内置默认）")

    p = sub.add_parser("paths", help="校验并打印 vault 关键路径")
    add_vault_arg(p)
    p.set_defaults(fn=cmd_paths)

    p = sub.add_parser("raw", help="把转录等原始文字落进 raw/bilibili/<BV>/（写入一次，永不覆盖）")
    p.add_argument("--bv", required=True, help="BV 号（作目录名）")
    p.add_argument("--from", dest="from_dir", action="append",
                   help="转录所在目录，可重复传多个")
    p.add_argument("--title", help="视频标题（写进 info.json）")
    p.add_argument("--url", help="视频链接（写进 info.json）")
    p.add_argument("--parts", help="收录了哪些分P，如 1-5（写进 info.json）")
    add_vault_arg(p)
    p.set_defaults(fn=cmd_raw)

    p = sub.add_parser("log", help="向 wiki/log.md 追加一条标准格式记录")
    p.add_argument("--title", required=True)
    p.add_argument("--kind", default="ingest",
                   help="记录前缀，默认 ingest；也可用 doc/backup 等")
    p.add_argument("--date", help="默认今天")
    p.add_argument("--note", action="append", help="条目下的说明段落，可重复")
    add_vault_arg(p)
    p.set_defaults(fn=cmd_log)

    p = sub.add_parser("mention", help="查 wiki 里是否已有页面提到某 BV 号（查重）")
    p.add_argument("--bv", required=True)
    add_vault_arg(p)
    p.set_defaults(fn=cmd_mention)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
