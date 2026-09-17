#!/usr/bin/env python3
"""类 Linux 文件系统 API — 服务端

纯 GET 接口，规格见 API.md，安全妥协见 security.md。
运行: python3 app.py  （默认 0.0.0.0:8765，可用 PORT 环境变量覆盖）
数据: 同目录 data.db（SQLite，持久化）
"""
import os
import sqlite3
import threading
from contextlib import closing

from flask import Flask, jsonify, request

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.db")
PORT = int(os.environ.get("PORT", "8765"))

app = Flask(__name__)
app.json.ensure_ascii = False

_lock = threading.Lock()  # 全库写锁：串行化所有请求，保证 SQLite 一致性


# ---------- 存储层 ----------

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(db()) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS folders (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT NOT NULL,
                name TEXT NOT NULL,
                UNIQUE (user, name)
            );
            CREATE TABLE IF NOT EXISTS files (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user    TEXT NOT NULL,
                folder  TEXT NOT NULL DEFAULT '',   -- '' 表示根目录，否则为文件夹名
                name    TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                tags    TEXT NOT NULL DEFAULT '',
                UNIQUE (user, folder, name)
            );
            CREATE TABLE IF NOT EXISTS state (
                user    TEXT PRIMARY KEY,
                current TEXT NOT NULL DEFAULT ''   -- current_folder，'' 表示根目录
            );
            """
        )
        conn.commit()


def get_state(conn, user):
    """返回 current_folder；用户首次出现自动初始化为根目录。"""
    row = conn.execute(
        "SELECT current FROM state WHERE user = ?", (user,)
    ).fetchone()
    if row is None:
        conn.execute("INSERT INTO state (user, current) VALUES (?, '')", (user,))
        return ""
    return row["current"]


# ---------- 响应辅助 ----------

def ok(**data):
    data["ok"] = True
    return jsonify(data)


def err(code, message):
    return jsonify({"ok": False, "error": message}), code


def require_user():
    user = request.args.get("user")
    if not user:
        return None
    return user


# ---------- 接口 ----------

@app.get("/cd")
def cd():
    user = require_user()
    if user is None:
        return err(400, "missing user")
    name = request.args.get("name", "")
    with _lock, closing(db()) as conn:
        get_state(conn, user)
        if name == "":  # 不传 name 回根目录
            conn.execute("UPDATE state SET current = '' WHERE user = ?", (user,))
            conn.commit()
            return ok(current_folder="")
        row = conn.execute(
            "SELECT 1 FROM folders WHERE user = ? AND name = ?", (user, name)
        ).fetchone()
        if row is None:
            return err(404, "no such folder")
        conn.execute("UPDATE state SET current = ? WHERE user = ?", (name, user))
        conn.commit()
        return ok(current_folder=name)


@app.get("/mkdir")
def mkdir():
    user = require_user()
    if user is None:
        return err(400, "missing user")
    name = request.args.get("name", "")
    if name == "":
        return err(400, "missing name")
    with _lock, closing(db()) as conn:
        current = get_state(conn, user)
        if current != "":
            return err(400, "mkdir only allowed in root")
        if conn.execute(
            "SELECT 1 FROM folders WHERE user = ? AND name = ?", (user, name)
        ).fetchone():
            return err(409, "folder already exists")
        if conn.execute(
            "SELECT 1 FROM files WHERE user = ? AND folder = '' AND name = ?",
            (user, name),
        ).fetchone():
            return err(409, "file already exists")
        conn.execute("INSERT INTO folders (user, name) VALUES (?, ?)", (user, name))
        conn.commit()
        return ok(name=name)


@app.get("/write")
def write():
    user = require_user()
    if user is None:
        return err(400, "missing user")
    name = request.args.get("name", "")
    if name == "":
        return err(400, "missing name")
    content = request.args.get("content", "")
    tags = request.args.get("tags", "")
    with _lock, closing(db()) as conn:
        current = get_state(conn, user)
        if conn.execute(
            "SELECT 1 FROM files WHERE user = ? AND folder = ? AND name = ?",
            (user, current, name),
        ).fetchone():
            return err(409, "file already exists")
        if current == "" and conn.execute(
            "SELECT 1 FROM folders WHERE user = ? AND name = ?", (user, name)
        ).fetchone():
            return err(409, "folder already exists")
        cur = conn.execute(
            "INSERT INTO files (user, folder, name, content, tags) VALUES (?, ?, ?, ?, ?)",
            (user, current, name, content, tags),
        )
        conn.commit()
        # 回显实际写入的 content：参数拼写错误（如 contect）会被静默忽略，
        # 调用方核对回显值即可发现内容未写入
        return ok(id=cur.lastrowid, name=name, content=content)


@app.get("/ls")
def ls():
    user = require_user()
    if user is None:
        return err(400, "missing user")
    with _lock, closing(db()) as conn:
        current = get_state(conn, user)
        folders = (
            [
                r["name"]
                for r in conn.execute(
                    "SELECT name FROM folders WHERE user = ? ORDER BY name", (user,)
                )
            ]
            if current == ""
            else []
        )
        files = [
            r["name"]
            for r in conn.execute(
                "SELECT name FROM files WHERE user = ? AND folder = ? ORDER BY name",
                (user, current),
            )
        ]
        return ok(current_folder=current, folders=folders, files=files)


@app.get("/cat")
def cat():
    user = require_user()
    if user is None:
        return err(400, "missing user")
    name = request.args.get("name", "")
    if name == "":
        return err(400, "missing name")
    with _lock, closing(db()) as conn:
        current = get_state(conn, user)
        row = conn.execute(
            "SELECT id, name, content, tags FROM files"
            " WHERE user = ? AND folder = ? AND name = ?",
            (user, current, name),
        ).fetchone()
        if row is None:
            return err(404, "no such file")
        return ok(id=row["id"], name=row["name"], tags=row["tags"], content=row["content"])


@app.get("/del")
def delete():
    user = require_user()
    if user is None:
        return err(400, "missing user")
    name = request.args.get("name", "")
    if name == "":
        return err(400, "missing name")
    with _lock, closing(db()) as conn:
        current = get_state(conn, user)
        row = conn.execute(
            "SELECT id FROM files WHERE user = ? AND folder = ? AND name = ?",
            (user, current, name),
        ).fetchone()
        if row:
            conn.execute("DELETE FROM files WHERE id = ?", (row["id"],))
            conn.commit()
            return ok(deleted=name)
        if current == "":
            folder = conn.execute(
                "SELECT id FROM folders WHERE user = ? AND name = ?", (user, name)
            ).fetchone()
            if folder:
                n = conn.execute(
                    "SELECT COUNT(*) AS n FROM files WHERE user = ? AND folder = ?",
                    (user, name),
                ).fetchone()["n"]
                if n:
                    return err(409, "folder not empty")
                conn.execute("DELETE FROM folders WHERE id = ?", (folder["id"],))
                conn.commit()
                return ok(deleted=name)
        return err(404, "no such file")


# ---------- 杂项 ----------

@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


@app.errorhandler(404)
def unknown_path(_):
    return err(404, "unknown endpoint")


@app.errorhandler(400)
def bad_request(_):
    return err(400, "malformed query string")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=PORT, threaded=True)
