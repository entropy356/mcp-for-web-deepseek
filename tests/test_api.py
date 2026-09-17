#!/usr/bin/env python3
"""类 Linux 文件系统 API — 全量接口测试
前置: 服务运行于 http://127.0.0.1:8765（测试使用独立用户，互不干扰）
"""
import os
import sys
import requests

BASE = os.environ.get("API_BASE", "http://127.0.0.1:3000")
passed, failed = [], []


def call(note, expect, path, params=None):
    r = requests.get(BASE + path, params=params)
    try:
        body = r.json()
    except Exception:
        body = r.text
    good = r.status_code == expect
    (passed if good else failed).append(note)
    mark = "PASS" if good else "FAIL"
    print(f"[{mark}] {note}: {r.status_code} (expect {expect}) {body if not good else ''}")
    return body


def check(note, cond, detail=""):
    (passed if cond else failed).append(note)
    print(f"[{'PASS' if cond else 'FAIL'}] {note} {detail if not cond else ''}")


U = "tester"


def cleanup(user):
    """清理指定用户的全部数据，保证测试可重复执行。"""
    requests.get(BASE + "/ls", params={"user": user})  # 确保用户存在
    b = requests.get(BASE + "/ls", params={"user": user}).json()
    for fd in b.get("folders", []):
        requests.get(BASE + "/cd", params={"user": user, "name": fd})
        for f in requests.get(BASE + "/ls", params={"user": user}).json().get("files", []):
            requests.get(BASE + "/del", params={"user": user, "name": f})
        requests.get(BASE + "/cd", params={"user": user})
        requests.get(BASE + "/del", params={"user": user, "name": fd})
    for f in requests.get(BASE + "/ls", params={"user": user}).json().get("files", []):
        requests.get(BASE + "/del", params={"user": user, "name": f})


cleanup(U)
cleanup("bob")


# --- 用户首次出现，自动初始化为根目录 ---
b = call("ls 首次出现初始化", 200, "/ls", {"user": U})
check("初始 current_folder 为根", b.get("current_folder") == "" and b.get("folders") == [] and b.get("files") == [])

# --- mkdir ---
call("mkdir 成功", 200, "/mkdir", {"user": U, "name": "docs"})
call("mkdir 重名 409", 409, "/mkdir", {"user": U, "name": "docs"})
call("mkdir 缺 name 400", 400, "/mkdir", {"user": U})
call("mkdir 空 name 400", 400, "/mkdir", {"user": U, "name": ""})
call("mkdir 缺 user 400", 400, "/mkdir")

# --- cd ---
call("cd 进入文件夹", 200, "/cd", {"user": U, "name": "docs"})
b = call("cd 后 ls", 200, "/ls", {"user": U})
check("current_folder=docs", b.get("current_folder") == "docs", str(b))
call("cd 不存在文件夹 404", 404, "/cd", {"user": U, "name": "nope"})
call("mkdir 不在根目录 400", 400, "/mkdir", {"user": U, "name": "sub"})
call("cd 不传 name 回根", 200, "/cd", {"user": U})
b = call("回根后 ls", 200, "/ls", {"user": U})
check("回根成功", b.get("current_folder") == "" and b.get("folders") == ["docs"], str(b))

# --- write（根目录）---
b = call("write 成功返回 id", 200, "/write", {"user": U, "name": "readme.txt", "content": "hello", "tags": "work,重要"})
check("write 返回新 id", isinstance(b.get("id"), int), str(b))
check("write 回显 content", b.get("content") == "hello", str(b))
b = call("write 未知参数被忽略", 200, "/write", {"user": U, "name": "typo.txt", "contect": "oops"})
check("拼错参数时回显空 content 可发现", b.get("content") == "", str(b))
call("del typo.txt 清理", 200, "/del", {"user": U, "name": "typo.txt"})
call("write 同名 409", 409, "/write", {"user": U, "name": "readme.txt"})
call("write 与文件夹同名 409", 409, "/write", {"user": U, "name": "docs"})
call("write 缺 name 400", 400, "/write", {"user": U})
call("write 空 name 400", 400, "/write", {"user": U, "name": ""})

# --- cat ---
b = call("cat 成功", 200, "/cat", {"user": U, "name": "readme.txt"})
check("cat 内容正确", b.get("content") == "hello" and b.get("tags") == "work,重要", str(b))
call("cat 不存在 404", 404, "/cat", {"user": U, "name": "nope.txt"})

# --- 文件夹内读写 ---
call("cd docs", 200, "/cd", {"user": U, "name": "docs"})
call("write 子目录文件", 200, "/write", {"user": U, "name": "inner.txt", "content": "in docs"})
call("cat 子目录文件", 200, "/cat", {"user": U, "name": "inner.txt"})
b = call("ls 子目录", 200, "/ls", {"user": U})
check("子目录只含文件", b.get("folders") == [] and b.get("files") == ["inner.txt"], str(b))
call("cat 根目录文件不可见 404", 404, "/cat", {"user": U, "name": "readme.txt"})

# --- del ---
call("cd 回根", 200, "/cd", {"user": U})          # 此时 docs 内仍有 inner.txt
call("del 非空文件夹 409", 409, "/del", {"user": U, "name": "docs"})
call("cd docs", 200, "/cd", {"user": U, "name": "docs"})
call("del 文件夹内文件", 200, "/del", {"user": U, "name": "inner.txt"})
call("del 不存在 404", 404, "/del", {"user": U, "name": "inner.txt"})
call("cd 回根", 200, "/cd", {"user": U})
call("del 根目录文件", 200, "/del", {"user": U, "name": "readme.txt"})
call("del 空文件夹", 200, "/del", {"user": U, "name": "docs"})
call("del 已删除文件夹 404", 404, "/del", {"user": U, "name": "docs"})

# --- 与文件夹同名互斥（先建文件后建文件夹）---
call("write file.txt", 200, "/write", {"user": U, "name": "file.txt"})
call("mkdir 与文件同名 409", 409, "/mkdir", {"user": U, "name": "file.txt"})
call("del file.txt", 200, "/del", {"user": U, "name": "file.txt"})

# --- 中文与空格的百分号编码（用独立用户，避免触碰 admin 演示数据）---
CU = "cjk_tester"
cleanup(CU)
r = requests.get(BASE + "/write?user=" + CU + "&name=%E6%88%91%E7%9A%84%20%E7%AC%94%E8%AE%B0.txt&content=%E4%B8%AD%E6%96%87%E5%86%85%E5%AE%B9")
check("中文+空格编码 write 200", r.status_code == 200, r.text)
r = requests.get(BASE + "/cat?user=" + CU + "&name=%E6%88%91%E7%9A%84%20%E7%AC%94%E8%AE%B0.txt")
check("中文+空格编码 cat 200", r.status_code == 200 and r.json().get("content") == "中文内容", r.text)
check("响应为 JSON+UTF-8", "application/json" in r.headers.get("Content-Type", ""), r.headers.get("Content-Type", ""))
r = requests.get(BASE + "/del?user=" + CU + "&name=%E6%88%91%E7%9A%84%20%E7%AC%94%E8%AE%B0.txt")
check("中文+空格编码 del 200", r.status_code == 200, r.text)

# --- 多用户隔离 ---
call("用户B mkdir", 200, "/mkdir", {"user": "bob", "name": "b_only"})
call("用户A看不到B", 404, "/cd", {"user": U, "name": "b_only"})

# --- 空 user ---
call("空 user 400", 400, "/ls", {"user": ""})

print(f"\n===== {len(passed)} passed, {len(failed)} failed =====")
sys.exit(1 if failed else 0)
