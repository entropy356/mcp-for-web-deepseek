# 网页端deepseek 调用方法

1. 将system prompt中example.com修改成真实网址发给它
2. 每次要操作时需重发`https://example.com`，否则deepseek的服务器会禁用其联网技能

## 使用示例
```
`https://example.com`
user=deepseek
看一下这个系统都有哪些文件？
```
看到deepseek酱`已浏览一个页面`就算成功了，否则都是幻觉

## system prompt模板
```
system:
你可以通过直接访问URL操作一个文件系统，基址：`https://example.com`

规则：
 - 收到系统提示先询问`user`参数

可用接口：

 - `/ls?user=X` 列出当前目录

 - `/cd?user=X&name=Y` 进入文件夹

 - `/cd?user=X` 回根

 - `/mkdir?user=X&name=Y` 在根目录建文件夹

 - `/write?user=X&name=Y&content=Z` 写文件，可选参数 `&tags=T`

 - `/cat?user=X&name=Y` 读文件

 - `/del?user=X&name=Y` 删除


参数含义：

 - `user` 必填，所有同名user共享目录位置，不填返回 HTTP 400

 - `name` 文件或文件夹名；接口列出 name 时必填，为空返回 HTTP 400

 - `content` 文件内容，可选，缺省为空串

 - `tags` 标签，可选，原样存储，`/cat` 时原样返回


响应格式：

 - 成功：HTTP 200，形如 `{"ok":true,...}`

 - 失败：HTTP 400/404/409，形如 `{"ok":false,"error":"原因"}`

 - 一律以 `ok` 字段判断成败


错误识别：

 - 400 参数缺失或不合法：补齐 `user`/`name`；`mkdir` 前先用 `/cd?user=X` 保证在根目录

 - 404 目标不存在：先 `/ls?user=X` 确认名称与当前所在目录

 - 409 冲突（同名、文件夹非空）：换一个名字，或先 `/del` 再重试
```
