# Claude 任務看板

Claude Code 在各機器(Mac / Ubuntu / Office)做的任務與研究進度,一頁總覽。

**看板:** https://mansonliu.github.io/claude-task-board/

## 怎麼運作

- `tasks.json` 是唯一資料來源。
- `index.html` 在瀏覽器讀 `tasks.json` 渲染成看板(響應式 + 暗色)。
- `task.py` 是 CLI,Claude 在任何機器做事時呼叫它新增/更新任務,自動 commit + push。

## ⚠️ 去識別規則(重要)

這是**公開 repo**。`title` 與 `note` 一律去識別:

- 不得含病患姓名、病歷號、可識別的個案細節。
- 醫學任務用抽象描述(例:「甲狀腺指引更新文」可,「王先生甲狀腺結節報告」不可)。

## task.py 用法

```bash
python3 task.py add "甲狀腺指引更新文" --cat blog          # 預設狀態 in_progress
python3 task.py add "整理講演投影片" --status todo --cat lecture
python3 task.py start <id>                                  # 標記進行中
python3 task.py done  <id>                                  # 標記完成
python3 task.py block <id> --note "等使用者回覆"            # 標記卡住
python3 task.py update <id> --note "PMID 已驗" --cat blog   # 改欄位
python3 task.py rm    <id>
python3 task.py list                                        # 終端列出,不動 git
```

加 `--no-push` 只改檔不推。`--machine` 預設依作業系統自動判斷(Darwin→Mac、Linux→Ubuntu、Windows→Office)。

## tasks.json schema

```json
{
  "updated": "2026-06-14",
  "tasks": [
    {
      "id": "guideline-blog-thyroid",   // 唯一,通常由標題自動產生
      "title": "甲狀腺疾病指引更新系列文",
      "status": "in_progress",          // in_progress | blocked | todo | done
      "machine": "Mac",                 // Mac | Ubuntu | Office
      "category": "blog",               // 自由字串:blog/lecture/harness/research/...
      "created": "2026-06-10",
      "updated": "2026-06-14",
      "note": "短描述"
    }
  ]
}
```

## 在另一台機器設定

```bash
git clone https://github.com/mansonliu/claude-task-board.git ~/claude-task-board
```

之後 Claude 在該機器即可用 `python3 ~/claude-task-board/task.py ...` 維護。
