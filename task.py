#!/usr/bin/env python3
"""Claude 任務看板 CLI — 在任何機器一行指令維護 tasks.json 並自動 push。

用法範例:
  python3 task.py add "甲狀腺指引更新文" --cat blog              # 預設 in_progress
  python3 task.py add "整理講演投影片" --status todo --cat lecture
  python3 task.py update guideline-blog-thyroid --note "PMID 已驗"
  python3 task.py done task-board
  python3 task.py block <id> --note "等使用者回覆"
  python3 task.py rm <id>
  python3 task.py list

去識別規則:title / note 不得含病患資訊;醫學任務用抽象描述(repo 是公開的)。
"""
import argparse, json, os, platform, re, subprocess, sys
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "tasks.json")
STATUSES = ["in_progress", "blocked", "todo", "done"]


def today():
    # 三台機器都在台灣,本機日期即可
    return date.today().isoformat()


def detect_machine():
    sysname = platform.system()
    host = platform.node().lower()
    if sysname == "Windows":
        return "Office"
    if sysname == "Linux":
        return "Ubuntu"
    if sysname == "Darwin":
        return "Mac"
    return host or "?"


def slugify(title):
    s = re.sub(r"[^\w一-鿿]+", "-", title.strip().lower())
    s = s.strip("-")
    return s[:48] or "task"


def load():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def save(data):
    data["updated"] = today()
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def find(data, tid):
    for t in data["tasks"]:
        if t["id"] == tid:
            return t
    return None


def unique_id(data, base):
    ids = {t["id"] for t in data["tasks"]}
    if base not in ids:
        return base
    i = 2
    while f"{base}-{i}" in ids:
        i += 1
    return f"{base}-{i}"


def git_sync():
    """任何操作前先拉最新看板——看板常在多台機器間更新,先同步再動手。"""
    try:
        subprocess.run(["git", "-C", ROOT, "pull", "--rebase", "--autostash", "-q"], check=True)
    except subprocess.CalledProcessError as e:
        subprocess.run(["git", "-C", ROOT, "rebase", "--abort"],
                       stderr=subprocess.DEVNULL, check=False)
        print(f"⚠ git pull 失敗（可能離線）,以本機版本繼續: {e}", file=sys.stderr)


def git_push(msg, no_push):
    if no_push:
        print("（--no-push,略過 git）")
        return
    try:
        subprocess.run(["git", "-C", ROOT, "add", "tasks.json"], check=True)
        subprocess.run(["git", "-C", ROOT, "commit", "-q", "-m", msg], check=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠ git commit 失敗（檔已存）: {e}", file=sys.stderr)
        return
    # push 被拒（他機剛推）時自動 rebase 一次再推
    for attempt in (1, 2):
        try:
            subprocess.run(["git", "-C", ROOT, "push", "-q"], check=True)
            print("✓ 已 push")
            return
        except subprocess.CalledProcessError:
            if attempt == 1:
                git_sync()
    print("⚠ git push 失敗（檔已 commit,可手動 push）", file=sys.stderr)


def cmd_add(data, a):
    tid = unique_id(data, a.id or slugify(a.title))
    t = {
        "id": tid,
        "title": a.title,
        "status": a.status,
        "machine": a.machine or detect_machine(),
        "category": a.cat or "general",
        "created": today(),
        "updated": today(),
        "note": a.note or "",
    }
    data["tasks"].append(t)
    print(f"+ {tid}  [{t['status']}]  {t['title']}")
    return f"add: {t['title']}"


def cmd_update(data, a):
    t = find(data, a.id)
    if not t:
        sys.exit(f"找不到 id: {a.id}")
    if a.status:
        t["status"] = a.status
    if a.title:
        t["title"] = a.title
    if a.cat:
        t["category"] = a.cat
    if a.machine:
        t["machine"] = a.machine
    if a.note is not None:
        t["note"] = a.note
    t["updated"] = today()
    print(f"~ {t['id']}  [{t['status']}]  {t['title']}")
    return f"update: {t['title']}"


def set_status(data, tid, status):
    t = find(data, tid)
    if not t:
        sys.exit(f"找不到 id: {tid}")
    t["status"] = status
    t["updated"] = today()
    print(f"~ {t['id']}  → {status}")
    return f"{status}: {t['title']}"


def cmd_rm(data, a):
    t = find(data, a.id)
    if not t:
        sys.exit(f"找不到 id: {a.id}")
    data["tasks"].remove(t)
    print(f"- {a.id}")
    return f"rm: {t['title']}"


def cmd_list(data, a):
    order = {s: i for i, s in enumerate(STATUSES)}
    for t in sorted(data["tasks"], key=lambda x: (order.get(x["status"], 9), x["id"])):
        print(f"{t['status']:>12}  {t['id']:<28} {t.get('machine',''):<7} {t['title']}")
    return None


def main():
    p = argparse.ArgumentParser(description="Claude 任務看板 CLI")
    p.add_argument("--no-push", action="store_true", help="只改檔不 git push")
    # 共用 parent,讓 --no-push 放在子指令後面也能用
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--no-push", action="store_true", help="只改檔不 git push")
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("add", help="新增任務", parents=[common])
    pa.add_argument("title")
    pa.add_argument("--id")
    pa.add_argument("--status", choices=STATUSES, default="in_progress")
    pa.add_argument("--cat")
    pa.add_argument("--machine")
    pa.add_argument("--note")

    pu = sub.add_parser("update", help="更新任務欄位", parents=[common])
    pu.add_argument("id")
    pu.add_argument("--status", choices=STATUSES)
    pu.add_argument("--title")
    pu.add_argument("--cat")
    pu.add_argument("--machine")
    pu.add_argument("--note")

    for name, st in [("done", "done"), ("block", "blocked"), ("start", "in_progress")]:
        sp = sub.add_parser(name, help=f"標記為 {st}", parents=[common])
        sp.add_argument("id")
        sp.add_argument("--note")

    pr = sub.add_parser("rm", help="刪除任務", parents=[common])
    pr.add_argument("id")

    sub.add_parser("list", help="列出所有任務")

    a = p.parse_args()
    if not getattr(a, "no_push", False):
        git_sync()  # 讀寫前都先同步,list 看到的也是最新看板
    data = load()

    if a.cmd in ("done", "block", "start"):
        st = {"done": "done", "block": "blocked", "start": "in_progress"}[a.cmd]
        if getattr(a, "note", None):
            t = find(data, a.id)
            if t:
                t["note"] = a.note
        msg = set_status(data, a.id, st)
    else:
        msg = {"add": cmd_add, "update": cmd_update, "rm": cmd_rm, "list": cmd_list}[a.cmd](data, a)

    if a.cmd == "list":
        return
    save(data)
    git_push(msg, a.no_push)


if __name__ == "__main__":
    main()
