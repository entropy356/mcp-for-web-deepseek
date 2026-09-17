# 类 Linux 文件系统 API — 使用文档

把文件当网址用：**在浏览器地址栏（或让 LLM 生成 URL）发起 GET 请求，即完成一次文件操作。**

- 服务基地址：`https://example.com`（本文所有示例以此占位，使用时替换为你的部署地址）
- 规格见 [API.md](API.md)，安全说明见 [security.md](security.md)

---

## 一、两分钟上手

下面 5 条演示路径，**与基地址拼接后在浏览器访问即真实执行**（使用独立用户 `demo`，与 `admin` 互不影响）：

| 步骤 | 点击这个链接 | 效果 |
|------|-------------|------|
| 1. 建文件夹 | `/mkdir?user=demo&name=notes` | 根目录下出现 `notes/` |
| 2. 写文件 | `/write?user=demo&name=first.txt&content=hello` | 当前目录（根）出现 `first.txt` |
| 3. 看目录 | `/ls?user=demo` | 列出文件夹与文件 |
| 4. 读文件 | `/cat?user=demo&name=first.txt` | 返回内容 `hello` |
| 5. 删文件 | `/del?user=demo&name=first.txt` | 文件被删除 |

> 完整 URL 需带上基地址，例如：`https://example.com/ls?user=demo`

---

## 二、通用约定

1. **全部为 GET 请求**，参数放在 Query String：`/{接口}?user=xxx&name=yyy`
2. **响应是 JSON**（UTF-8）：
   - 成功：HTTP 200 + `{"ok": true, ...}`
   - 失败：HTTP 400/404/409 + `{"ok": false, "error": "原因"}`
   - 判断成败看 `ok` 字段或 HTTP 状态码
3. **`user` 即身份**：每个 `user` 有独立空间，首次使用自动创建，无需注册
4. **服务端记住每个用户的位置**（`current_folder`）：`/write`、`/ls`、`/cat`、`/del` 只作用于当前所在目录；`/mkdir` 只能在根目录用

### 错误码

| 状态码 | 含义 | 常见情形与应对 |
|--------|------|----------------|
| 400 | 参数缺失或不合法 | 补齐 `user`/`name`；`mkdir` 前先确认在根目录（`/cd?user=xxx` 不带 name 即回根） |
| 404 | 目标不存在 | 检查拼写与当前目录；先用 `/ls` 确认 |
| 409 | 冲突 | 文件/文件夹同名 → 换名或先 `/del`；删文件夹 → 先清空其中文件 |

---

## 三、接口详解

### 1. `/ls` — 查看当前目录

```
/ls?user=admin
```

返回：

```json
{"current_folder":"", "folders":["folder_a","folder_b"], "files":["我的 笔记.txt"], "ok":true}
```

- 在根目录时 `folders` 列出所有文件夹；在子文件夹内时 `folders` 恒为空（文件夹只有一层，都挂在根下）。

### 2. `/cd` — 切换目录

```
/cd?user=admin&name=folder_a    进入 folder_a
/cd?user=admin                  不带 name → 回根目录
```

返回 `{"current_folder":"folder_a","ok":true}`。目标文件夹不存在报 404。

### 3. `/mkdir` — 新建文件夹（仅限根目录）

```
/mkdir?user=admin&name=project
```

- 当前不在根目录 → 400；与根下文件或文件夹重名 → 409。
- 建完通常紧跟 `/cd` 进入，或留在根目录直接 `/write`。

### 4. `/write` — 创建文件

```
/write?user=admin&name=log.txt&content=第一行内容&tags=日记
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `user` | 是 | 用户名 |
| `name` | 是 | 文件名，为空报 400 |
| `content` | 否 | 文件内容，缺省为空串 |
| `tags` | 否 | 标签，原样存储、`/cat` 时原样返回 |

返回新文件 id 与**实际写入的 content**：`{"id":1,"name":"log.txt","content":"第一行内容","ok":true}`。核对回显的 `content`：若与你打算写的不符（尤其为空），说明参数名拼错（正确写法是 `content`），改正后重新写入。当前目录已有同名文件（或根目录下与文件夹同名）报 409。

### 5. `/cat` — 读文件

```
/cat?user=admin&name=log.txt
```

返回：`{"id":1,"name":"log.txt","tags":"日记","content":"第一行内容","ok":true}`。不存在报 404。

### 6. `/del` — 删除

```
/del?user=admin&name=log.txt      删当前目录的文件
/del?user=admin&name=project      删根目录的空文件夹
```

- 文件夹非空 → 409；目标不存在 → 404。
- **删除即永久删除，无回收站。**

---

## 四、百分号编码速查

参数值里的**非字母数字字符**要百分号编码（浏览器地址栏通常自动完成；curl、LLM 生成 URL 时必须手动处理）：

| 原字符 | 编码后 | 说明 |
|--------|--------|------|
| 空格 | `%20` | |
| `&` | `%26` | 不编码会被当成参数分隔符 |
| `=` | `%3D` | 不编码会破坏键值对 |
| `#` | `%23` | 不编码会被当成锚点 |
| `%` | `%25` | 必须最先编码 |
| `+` | `%2B` | |
| 中文 | 逐字节编码 | "文"= `%E6%96%87`，"档"= `%E6%A1%A3` |

**完整示例**——文件名"我的 笔记.txt"：

```
/write?user=admin&name=%E6%88%91%E7%9A%84%20%E7%AC%94%E8%AE%B0.txt&content=hello
```

字母、数字、`-`、`_`、`.`、`~` 无需编码（如 `log.txt`、`my-note_v2`）。

**curl 注意**：URL 含 `&` 时必须整体加引号，否则 shell 会截断命令：

```bash
curl "http://…/write?user=admin&name=log.txt&content=hello"
```

---

## 五、给 LLM 的调用指引

 [PROMPT.md](PROMPT.md)。

---

## 六、典型场景

**场景 A — 会话存档**：对话结束前，让 LLM 把结论写成文件：
```
/write?user=admin&name=2026-09-17会议结论.txt&content=…&tags=会议
```
下次开场 `/cat` 读回，即可恢复上下文。

**场景 B — 分类整理**：根目录 `/mkdir` 建分类 → `/cd` 进入 → `/write` 归档文件。`/ls` 根目录即为目录页。

**场景 C — 让 LLM 维护结构化笔记**：约定固定文件名（如 `todo.txt`），每次 `/cat` 读出 → 修改 → 重新 `/write` 覆盖思路见下注。

> 注：`/write` 不覆盖同名文件（报 409）。更新内容的标准流程：`/cat` 取出 → 处理 → `/del` 旧文件 → `/write` 新文件。

---

## 七、注意事项

- **无认证**：`user` 即身份，知道名字即可操作。链接勿发给不可信的人；公网地址泄露可要求下线。
- **URL 长度**：浏览器/网关一般限 2–8 KB，`content` 建议 ≤1KB。
- **GET 有副作用**：浏览器预取、爬虫、链接预览可能意外触发写操作；写操作 URL 不要随意贴到公开网页。
- **一层目录**：文件夹只挂在根下、不能嵌套；文件夹之间靠命名约定分层（如 `work-2026`）。
