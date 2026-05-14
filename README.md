# AI HOT 日报 → 飞书推送

每天北京时间 09:00 自动推送 [AI HOT](https://aihot.virxact.com) 日报到飞书群。周一额外推送近三日动态汇总。

数据覆盖：模型发布、产品更新、行业动态、论文研究、技巧观点。

## 食用方式

### 1. 创建飞书机器人

打开你要接收日报的飞书群 → 群设置 → **群机器人** → **添加机器人** → 搜索 **自定义机器人**，添加后复制 Webhook URL。

> Webhook URL 形如 `https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx`。IP 白名单不用勾，GitHub Actions 的 IP 不固定。

### 2. Fork 本仓库

点右上角 **Fork**，把仓库复制到你的 GitHub 账号下。

### 3. 配置 Secret

在你 Fork 的仓库页面：**Settings → Secrets and variables → Actions → New repository secret**

- **Name**: `FEISHU_WEBHOOK_URL`
- **Secret**: 第1步复制的飞书 Webhook URL

### 4. 验证

进到你 Fork 仓库的 **Actions** 标签页，找到 "AI HOT 日报推送" workflow，点 **Run workflow** 手动触发一次测试。

---

之后每天北京时间 09:00 自动推送，不用管了。
