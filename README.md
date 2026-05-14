# AI HOT 日报 → 飞书推送

每天北京时间 09:00 自动推送 AI HOT 日报到飞书群。周一额外推送近三日动态汇总。

## 部署步骤

### 1. 创建飞书机器人

1. 打开你要接收日报的飞书群 → 群设置 → **群机器人** → **添加机器人**
2. 搜索 **自定义机器人**，添加
3. 复制 Webhook URL（形如 `https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx`）
4. 可以勾选 **IP 白名单**（GitHub Actions 的 IP 不固定，建议不勾）

### 2. 推送代码到 GitHub

```bash
# 在 GitHub 上新建一个仓库（私有仓库即可）
# 然后在本地执行：
cd ai-daily-feishu
git init
git add .
git commit -m "init: AI HOT daily report to Feishu"
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

### 3. 配置 Secrets

在 GitHub 仓库页面：
**Settings → Secrets and variables → Actions → New repository secret**

- **Name**: `FEISHU_WEBHOOK_URL`
- **Secret**: 第1步复制的飞书 Webhook URL

### 4. 验证

进到仓库的 **Actions** 标签页，能看到已自动创建的 workflow。
也可以点 **Run workflow** 手动触发一次测试。
