# 类 Linux 文件系统 API — 核心文档

## 一、需求
 - 一个只通过GET请求行实现信息交换的文件api，实现让deepseek网页版可调用
 - 所有安全方面的妥协在security文档补充

## 二、设计方案

### 目录结构

```
根目录 ('' 空字符串表示)
├── folder_a/
├── folder_b/
└── (文件)
```

- 所有文件夹挂在根下。
- 每个用户拥有 `current_folder`，首次出现自动初始化为根目录。
- 所有读写仅作用于当前目录。
- 根目录下，文件名与文件夹名不得重复。

### 编码格式

- 请求与响应均为 **UTF-8**。
- URL 中的参数值需 **百分号编码**（Percent-encoding）：
  - 空格 → `%20`
  - 中文 → UTF-8 字节逐字节编码，如"文档" → `%E6%96%87%E6%A1%A3`
  - 保留字符如 `&`、`=`、`#`、`%` 必须编码，否则破坏 Query String 结构
- 响应体为 JSON，`Content-Type: application/json; charset=utf-8`。
- 示例：
  - 文件名为"我的 笔记.txt"：
    `/write?user=admin&name=%E6%88%91%E7%9A%84%20%E7%AC%94%E8%AE%B0.txt`
- 客户端（浏览器、curl、LLM 生成 URL 时）自行负责编码，服务端不解码的参数值视为字面值。

### URL格式

所有请求方法为 **GET**，参数通过 Query String 传递。

通用格式：
`/{接口}?{参数名}={参数值}&...`

示例：
- 进入文件夹：`/cd?user=admin&name=docs`
- 新建文件夹：`/mkdir?user=admin&name=project`
- 写入文件：`/write?user=admin&name=log.txt&content=hello`
- 列出目录：`/ls?user=admin`
- 读取文件：`/cat?user=admin&name=log.txt`
- 删除：`/del?user=admin&name=log.txt`

### 接口定义

| # | 接口 | 必填参数 | 可选参数 | 行为 |
|---|------|----------|----------|------|
| 1 | `/cd` | `user` | `name` | 不传 `name` 回根目录；传入则进入该文件夹；不存在报 404 |
| 2 | `/mkdir` | `user`, `name` | — | **仅限根目录下可用**（当前不在根目录报 400）；在根下新建文件夹；重名报 409 |
| 3 | `/write` | `user`, `name` | `content`, `tags` | 在当前目录创建文件，返回新 id 与写入的 content；同名报 409；name 为空报 400 |
| 4 | `/ls` | `user` | — | 列出当前目录下的文件与文件夹名称 |
| 5 | `/cat` | `user`, `name` | — | 读取当前目录中指定文件的内容；不存在报 404 |
| 6 | `/del` | `user`, `name` | — | 删除当前目录中指定名字的文件；根目录下也可删空文件夹；文件夹非空报 409 |

### 错误码约定

| 状态码 | 场景 |
|--------|------|
| 400 | 参数缺失或不合法；`mkdir` 时不在根目录 |
| 404 | 目标不存在 |
| 409 | 冲突（同名、文件夹非空） |
