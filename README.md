# mcp-for-web-deepseek

类 Linux 文件系统 API：**只用 GET 请求完成全部文件操作**，为 DeepSeek 网页版等无法直接执行工具调用的 LLM 设计——模型生成 URL 自动访问即执行写入、读取、删除。

## 特性

- 全部接口为 GET，参数走 Query String，LLM 生成 URL 即可调用
- 通过 `user` 实现记录当前目录
- 数据持久化（SQLite）

## 目录结构

```
mcp-for-web-deepseek/
├── README.md
├── docs/
│   ├── API.md        # 核心规格：目录模型、编码、接口定义、错误码
│   ├── USAGE.draft.md      # 使用文档：上手示例、编码速查、典型场景
│   ├── PROMPT.md     # 可直接复制给 LLM 的 system prompt 模板
│   └── security.md   # 安全妥协清单（部署前必读）
├── src/
│   └── app.py        # 服务端（Flask，单文件）
└── tests/
    └── test_api.py   # 53 项接口测试（幂等，可重复执行）
```

## 部署

### 依赖

- Python 3.10+
- Flask

```bash
pip install flask
```

### 运行

```bash
cd src
python3 app.py                  # 默认监听 0.0.0.0:8765
PORT=3000 python3 app.py        # 用 PORT 环境变量指定端口
```

数据落盘为运行目录下的 `data.db`（SQLite），备份即复制该文件。

### 验证

```bash
curl "http://127.0.0.1:3000/ls?user=admin"
# {"current_folder":"","files":[],"folders":[],"ok":true}
```

### 运行测试

服务启动后（默认指向 `http://127.0.0.1:3000`，可用 `API_BASE` 环境变量指向其他地址）：

```bash
python3 tests/test_api.py       # 53 项测试，连跑两遍验证幂等
```

### 生产环境

Flask 自带服务器仅用于开发，生产建议 gunicorn（暂不可直接用，可能解决方案见[^1]）：

```bash
pip install gunicorn
gunicorn -w 1 --threads 4 -b 0.0.0.0:3000 app:app
```

置于反向代理之后终止 TLS 即可。本文与 docs/ 中的示例地址统一使用 `https://example.com` 占位。

## 接口速查

| 接口 | 参数 | 行为 |
|------|------|------|
| `/ls` | `user` | 列出当前目录的文件与文件夹 |
| `/cd` | `user`，可选 `name` | 进入文件夹；不带 `name` 回根 |
| `/mkdir` | `user`, `name` | 在根目录新建文件夹（仅限根目录） |
| `/write` | `user`, `name`，可选 `content`, `tags` | 创建文件，返回新 id 与写入的 content |
| `/cat` | `user`, `name` | 读取文件内容 |
| `/del` | `user`, `name` | 删除文件；根目录下可删空文件夹 |

错误码：400 参数缺失或不合法；404 目标不存在；409 同名冲突或文件夹非空。完整规格见 [docs/API.md](docs/API.md)。

## 安全

**部署前必读 [docs/security.md](docs/security.md)**：本服务无任何认证，`user` 即身份，任何人可用任意用户名读写全部数据，仅适合可信私有环境。


## 说明
[^1]:
```
P0：按 README 推荐方式部署，必然 500。
 init_db() 待在 if __name__ == "__main__" 里，
而 README「生产环境」推荐的正是 gunicorn ... app:
app——这条路径 __name__ 是 "app"，建表永不执行。
干净目录下第一个请求就 no such table: state。
更有意思的是它为什么没被发现：只要曾经 python3 app.py 跑过一次留下 data.db，
gunicorn 就完全正常。作者的日常流程（先跑测试再换 gunicorn）刚好被自己的历史数据挡住了这个 bug。
修复只要一行：把 init_db() 挪到模块顶层。
```
