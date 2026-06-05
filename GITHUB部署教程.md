# 部署到GitHub Actions 定时执行教程

## 第一步：准备GitHub仓库

1. 如果还没有GitHub账号，请先注册一个
2. 在GitHub上创建一个新的仓库（Public或Private都可以）
3. 给仓库起个名字，比如 `finance-news-bot`

## 第二步：初始化Git仓库

在你的电脑上打开终端或命令行，进入finance目录（注意：是finance目录，不是子目录）：

```bash
cd c:\Users\18685\Desktop\finance
```

然后执行以下命令：

```bash
# 初始化Git仓库
git init

# 添加所有文件
git add .

# 提交到本地仓库
git commit -m "Initial commit"

# 重命名主分支为main
git branch -M main

# 添加远程仓库（替换为你的GitHub仓库地址）
git remote add origin https://github.com/你的用户名/你的仓库名.git
```

## 第三步：创建新分支并上传

```bash
# 创建一个新分支，比如叫deploy
git checkout -b deploy

# 推送新分支到GitHub
git push -u origin deploy
```

或者，如果你想推送到main分支：

```bash
git push -u origin main
```

## 第四步：配置GitHub Secrets

1. 打开你的GitHub仓库页面
2. 点击 `Settings`（设置）
3. 在左侧菜单找到 `Secrets and variables` → `Actions`
4. 点击 `New repository secret`，添加以下密钥：

| 密钥名称 | 值 | 示例 |
|--------|---|------|
| `OPENAI_API_KEY` | 你的DeepSeek API密钥 | `sk-xxxxxxxxxx` |
| `SMTP_HOST` | 邮件服务器 | `smtp.163.com` |
| `SMTP_PORT` | 邮件端口 | `465` |
| `SMTP_USER` | 发件人邮箱 | `18685329778@163.com` |
| `SMTP_PASSWORD` | 邮箱授权码 | `xxxxxxxxxx` |
| `RECIPIENT_EMAIL` | 收件人邮箱 | `18685329778@163.com` |

## 第五步：启用GitHub Actions

1. 推送代码后，在GitHub仓库页面点击 `Actions`
2. 你会看到 `Daily Finance News Job` 这个工作流
3. 点击进入，可以点击 `Run workflow` 手动触发测试一下

## 第六步：修改定时时间（可选）

当前已配置为每天3次推送：
- 北京时间9:00
- 北京时间12:00
- 北京时间17:00（下午5点）

如果你想修改执行时间，编辑 `.github/workflows/daily-job.yml` 文件中的 cron 表达式：

```yaml
- cron: '0 1 * * *'  # UTC时间1:00 = 北京时间9:00
- cron: '0 4 * * *'  # UTC时间4:00 = 北京时间12:00
- cron: '0 9 * * *'  # UTC时间9:00 = 北京时间17:00
```

常用的cron示例：
- 每天9:00：`0 1 * * *`
- 每天8:00：`0 0 * * *`
- 每天12:00：`0 4 * * *`
- 每小时执行：`0 * * * *`

## 第七步：查看执行结果

1. 在GitHub仓库的 `Actions` 页面可以看到每次执行记录
2. 点击具体的某次运行，可以看到详细日志
3. 如果生成了Word文档，可以在运行记录的下方 `Artifacts` 处下载

## 文件说明

- `.github/workflows/daily-job.yml`：GitHub Actions 配置文件
- `.gitignore`：指定不需要上传的文件（比如.env）
- `requirements.txt`：项目依赖包列表

## 注意事项

1. **不要把 `.env` 文件上传到GitHub**，这会泄露你的密钥
2. GitHub Actions 对于公开仓库是免费的
3. 定时任务执行时间以UTC时间为准
4. 如果执行失败，可以查看Actions日志了解原因

## 本地测试

在部署前，可以先在本地测试一下：

```bash
# 确保在项目目录下
cd c:\Users\18685\Desktop\finance\FinNewsCollectionBot

# 执行一次测试
..\.venv\Scripts\python.exe financebot.py --now
```

## 常见问题

**Q: 如何修改执行时间？**
A: 编辑 `.github/workflows/daily-job.yml` 中的 cron 表达式，然后提交并推送。

**Q: 邮件发送失败怎么办？**
A: 检查Secrets配置是否正确，特别是SMTP_PASSWORD（授权码不是邮箱密码）。

**Q: 可以手动触发吗？**
A: 可以，在Actions页面点击 `Run workflow` 按钮。

## 快速参考命令

```bash
# 查看当前分支
git branch

# 切换分支
git checkout branch-name

# 提交更改
git add .
git commit -m "描述你的更改"
git push

# 从GitHub拉取最新代码
git pull
```
