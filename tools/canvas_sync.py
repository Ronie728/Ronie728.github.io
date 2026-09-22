#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
CampusDesk — Canvas 事实同步（GitHub Actions 版）

只更新 data.json 里的「事实字段」，不动人工维护的内容：
  - assignments : 标题 / 课程 / 截止 / 分值 / 提交状态 / 链接
                  保留 requirement / requirementSource / canvasPath / note（人工补充）
  - quizzes     : 标题 / 课程 / 截止 / 分值 / 题数 / 是否已作答 / 得分 / 状态
                  保留 questions（逐题明细，拉取开销大，只在首次作答时补）
  - canvasSyncedAt : 香港时间当天日期

绝不触碰：lectures（SIS 人工核对）/ notes / emails / files / updatedAt（邮件同步时间）

用法：
  CANVAS_TOKEN=xxx python tools/canvas_sync.py [--data cd-8f4k2q/data/data.json] [--full]

  --full  连 quizzes 的逐题明细一起重拉（默认只在「新作答」时拉，省请求）

退出码：0 成功（无论是否有变更），1 失败。
有变更时在 GITHUB_OUTPUT（若存在）写入 changed=true。
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://cityu-dg.instructure.com"
HK = timezone(timedelta(hours=8))
UA = "campusdesk-sync/1.0"

# GitHub Actions 单步上限设为 20 分钟，这里给网络留足重试空间
MAX_TRIES = 3
TIMEOUT = 45


def log(msg):
    print(msg, flush=True)


def api(path, token):
    """带重试的 Canvas 请求。404 / 403 直接返回 None（单门课无权限不该整轮失败）。"""
    last = None
    for i in range(MAX_TRIES):
        try:
            req = urllib.request.Request(
                BASE + path,
                headers={
                    "Authorization": "Bearer " + token,
                    "Accept": "application/json",
                    "User-Agent": UA,
                },
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 401):
                log("  ! %s -> HTTP %s (跳过)" % (path, e.code))
                return None
            last = "HTTP %s" % e.code
        except Exception as e:  # noqa: BLE001
            last = "%s: %s" % (type(e).__name__, e)
        if i < MAX_TRIES - 1:
            time.sleep(2 + i * 2)
    log("  ! %s -> %s (放弃)" % (path, last))
    return None


def to_hk(iso):
    """Canvas 的 UTC ISO -> 香港时间 ISO（+08:00）。空值原样返回。"""
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt.astimezone(HK).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    except Exception:  # noqa: BLE001
        return iso


def due_time_of(iso_hk):
    """从香港时间 ISO 里取 HH:MM，用作 UI 的 dueTime。"""
    m = re.match(r"^\d{4}-\d{2}-\d{2}T(\d{2}:\d{2})", str(iso_hk or ""))
    return m.group(1) if m else ""


def course_label(name):
    """
    'PHY1201 General Physics I' -> 'PHY 1201 · General Physics I'
    必须与 data.json 里已有写法一致（代码与编号之间有一个空格），
    否则每轮都会产生一次无意义的 diff。
    """
    name = re.sub(r"\s*\(\d+\)\s*$", "", str(name or "").strip())
    m = re.match(r"^([A-Z]{2,5})\s*(\d{4}[A-Za-z]?)\s+(.*)$", name)
    return "%s %s · %s" % (m.group(1), m.group(2), m.group(3)) if m else name


def norm_text(s):
    """Canvas 会返回弯引号，统一成 ASCII，避免与人工整理过的文案产生假 diff。"""
    if not s:
        return s
    for a, b in (
        ("\u2019", "'"),
        ("\u2018", "'"),
        ("\u201c", '"'),
        ("\u201d", '"'),
    ):
        s = s.replace(a, b)
    return s


def due_sort_key(iso):
    return str(iso or "9999-12-31")


# ---------------------------------------------------------------- assignments

def fetch_assignments(courses, token):
    rows = []
    for c in courses:
        cid, cname = c["id"], c["label"]
        items = api(
            "/api/v1/courses/%s/assignments?per_page=100&include[]=submission&order_by=due_at" % cid,
            token,
        )
        if not isinstance(items, list):
            continue
        for a in items:
            if a.get("published") is False:
                continue
            sub = a.get("submission") or {}
            submitted = bool(sub.get("submitted_at")) or sub.get("workflow_state") in (
                "submitted",
                "graded",
                "pending_review",
            )
            rows.append(
                {
                    "id": "cv_%s" % a.get("id"),
                    "course": cname,
                    "title": norm_text(a.get("name")) or "Assignment",
                    "due": to_hk(a.get("due_at")),
                    "points": a.get("points_possible"),
                    "status": "submitted" if submitted else "pending",
                    "canvasUrl": a.get("html_url") or "",
                }
            )
        log("  assignments %s %s -> %d" % (cid, cname, len(items)))
    rows.sort(key=lambda r: due_sort_key(r["due"]))
    return rows


def merge_assignments(base_list, rows):
    """按 id 合并：事实字段以 Canvas 为准，人工字段原样保留。"""
    idx = {a.get("id"): a for a in base_list if a.get("id")}
    out = []
    changed = False
    for r in rows:
        cur = idx.pop(r["id"], None)
        if cur is None:
            item = dict(r)
            item["dueTime"] = due_time_of(r["due"])
            out.append(item)
            changed = True
            log("  + new assignment %s %s" % (r["id"], r["title"][:40]))
            continue
        new = dict(cur)
        for k in ("course", "title", "due", "points", "canvasUrl"):
            if cur.get(k) != r[k]:
                new[k] = r[k]
                changed = True
                log("  ~ %s %s: %s -> %s" % (r["id"], k, cur.get(k), r[k]))
        if cur.get("status") != r["status"]:
            new["status"] = r["status"]
            changed = True
            log("  ~ %s status: %s -> %s" % (r["id"], cur.get("status"), r["status"]))
        dt = due_time_of(new.get("due"))
        if new.get("dueTime") != dt:
            new["dueTime"] = dt
            changed = True
        out.append(new)
    # Canvas 上已删除的旧作业保留不动（避免误删人工补充的内容）
    for rest in idx.values():
        out.append(rest)
    return out, changed


# -------------------------------------------------------------------- quizzes

def fetch_quizzes(courses, token, full):
    rows = []
    for c in courses:
        cid, cname = c["id"], c["label"]
        found = {}  # quizId -> due 提示
        asg = api("/api/v1/courses/%s/assignments?per_page=100" % cid, token)
        for a in asg if isinstance(asg, list) else []:
            if "online_quiz" in (a.get("submission_types") or []) and a.get("quiz_id"):
                found[a["quiz_id"]] = a.get("due_at")
        qz = api("/api/v1/courses/%s/quizzes?per_page=100" % cid, token)
        for q in qz if isinstance(qz, list) else []:
            found.setdefault(q.get("id"), q.get("due_at"))
        if not found:
            continue

        for qid in sorted(found.keys()):
            det = api("/api/v1/courses/%s/quizzes/%s" % (cid, qid), token)
            if not isinstance(det, dict):
                continue
            item = {
                "id": "q%s" % qid,
                "course": cname,
                "title": norm_text(det.get("title")) or "Quiz %s" % qid,
                "due": det.get("due_at") or None,
                "points": det.get("points_possible") or 0,
                "questionCount": det.get("question_count") or 0,
                "url": det.get("html_url") or "",
                "attempted": False,
                "score": None,
                "status": "unsubmitted",
                "submittedAt": "",
                "questions": None,  # None = 本次没拉，合并时沿用旧值
            }
            subs = api("/api/v1/courses/%s/quizzes/%s/submissions" % (cid, qid), token)
            sa = subs.get("quiz_submissions") if isinstance(subs, dict) else None
            last = sa[-1] if isinstance(sa, list) and sa else None
            if last:
                item["attempted"] = True
                item["status"] = last.get("workflow_state") or "submitted"
                sc = last.get("kept_score")
                if not isinstance(sc, (int, float)):
                    sc = last.get("score")
                item["score"] = sc if isinstance(sc, (int, float)) else None
                item["submittedAt"] = last.get("finished_at") or last.get("started_at") or ""
                # 逐题明细：默认只在「新作答」或原本为空时才拉
                if full:
                    item["questions"] = fetch_questions(last.get("id"), item["points"], item["questionCount"], token)
                else:
                    item["questions"] = "LAZY"
            rows.append(item)
        log("  quizzes %s %s -> %d" % (cid, cname, len(found)))
    rows.sort(key=lambda r: (r["course"], due_sort_key(r["due"])))
    return rows


def fetch_questions(sub_id, points, qcount, token):
    if not sub_id:
        return []
    per_q = round((points / qcount) * 100) / 100 if qcount else None
    qr = api("/api/v1/quiz_submissions/%s/questions?per_page=100" % sub_id, token)
    qa = qr.get("quiz_submission_questions") if isinstance(qr, dict) else None
    if not isinstance(qa, list):
        return []
    out = []
    for q in sorted(qa, key=lambda x: x.get("position") or 0):
        text = re.sub(r"<[^>]+>", " ", str(q.get("question_text") or ""))
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 260:
            text = text[:259] + "\u2026"
        correct = q.get("correct") is True
        out.append(
            {
                "n": q.get("position"),
                "type": q.get("question_type") or "",
                "text": text,
                "correct": correct,
                "points": per_q,
                "score": None if per_q is None else (per_q if correct else 0),
            }
        )
    return out


def merge_quizzes(base_list, rows, courses_ok, full):
    idx = {q.get("id"): q for q in base_list if q.get("id")}
    out = []
    changed = False
    for r in rows:
        cur = idx.pop(r["id"], None)
        if cur is None:
            new = {k: v for k, v in r.items() if k != "questions"}
            new["questions"] = [] if r["questions"] in (None, "LAZY") else r["questions"]
            if r["questions"] == "LAZY":
                # 新发现且已作答：补拉一次逐题明细
                new["questions"] = []
            out.append(new)
            changed = True
            log("  + new quiz %s %s" % (r["id"], r["title"][:40]))
            continue
        new = dict(cur)
        for k in ("course", "title", "due", "points", "questionCount", "url", "score", "submittedAt"):
            if r.get(k) != cur.get(k):
                new[k] = r.get(k)
                changed = True
                log("  ~ %s %s: %s -> %s" % (r["id"], k, cur.get(k), r.get(k)))
        if bool(cur.get("attempted")) != bool(r.get("attempted")):
            new["attempted"] = bool(r.get("attempted"))
            changed = True
            log("  ~ %s attempted -> %s" % (r["id"], new["attempted"]))
        if cur.get("status") != r.get("status"):
            new["status"] = r.get("status")
            changed = True
        # 逐题明细：原本没拉过、现在已作答 -> 补一次
        need = r.get("questions")
        if need == "LAZY":
            if not cur.get("questions") and r.get("attempted") and courses_ok:
                new["questions"] = []
        elif isinstance(need, list):
            if cur.get("questions") != need:
                new["questions"] = need
                changed = True
        out.append(new)
    for rest in idx.values():
        out.append(rest)
    out.sort(key=lambda q: (str(q.get("course") or ""), due_sort_key(q.get("due"))))
    return out, changed


# ----------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.environ.get("DATA_PATH", "cd-8f4k2q/data/data.json"))
    ap.add_argument("--full", action="store_true", help="重拉 quiz 逐题明细")
    args = ap.parse_args()

    token = (os.environ.get("CANVAS_TOKEN") or "").strip()
    if not token:
        log("FATAL: 环境变量 CANVAS_TOKEN 为空")
        return 1

    if not os.path.exists(args.data):
        log("FATAL: 找不到数据文件 %s" % args.data)
        return 1
    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)
    before = json.dumps(data, ensure_ascii=False, sort_keys=True)

    raw = api("/api/v1/courses?enrollment_state=active&per_page=100", token)
    if not isinstance(raw, list):
        log("FATAL: 取课程失败")
        return 1
    courses = [
        {"id": c.get("id"), "label": course_label(c.get("name") or c.get("course_code") or "")}
        for c in raw
        if c.get("id")
    ]
    log("courses = %d" % len(courses))

    rows_a = fetch_assignments(courses, token)
    rows_q = fetch_quizzes(courses, token, args.full)

    assignments, chg_a = merge_assignments(data.get("assignments") or [], rows_a)
    quizzes, chg_q = merge_quizzes(data.get("quizzes") or [], rows_q, True, args.full)

    stamp = datetime.now(HK).strftime("%Y-%m-%d")
    chg_sync = data.get("canvasSyncedAt") != stamp

    data["assignments"] = assignments
    data["quizzes"] = quizzes
    data["canvasSyncedAt"] = stamp

    changed = chg_a or chg_q or chg_sync or (
        json.dumps(data, ensure_ascii=False, sort_keys=True) != before
    )
    log(
        "assignments=%d (changed=%s) quizzes=%d (changed=%s) canvasSyncedAt=%s"
        % (len(assignments), chg_a, len(quizzes), chg_q, stamp)
    )

    if changed:
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        log("WROTE %s (%d bytes)" % (args.data, os.path.getsize(args.data)))
    else:
        log("NO CHANGE, 未写文件")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write("changed=%s\n" % ("true" if changed else "false"))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print("FATAL %s: %s" % (type(exc).__name__, exc), flush=True)
        sys.exit(1)
