# MBA — Metric Brand Auditor

`/mba` 文件夹下的 skill 名为 **Metric Brand Auditor**（MBA）。

## 环境配置

本项目使用阿里云无影 AgentBay 服务，需要你自行配置 API Key。

### 步骤

1. 复制示例文件：

   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env`，填入你的 API Key：

   ```
   WUYING_API_KEY=your_api_key_here
   WUYING_IMAGE_ID=browser_latest
   ```

3. 获取 API Key：前往 [阿里云无影控制台](https://wuying.aliyun.com) 创建 AgentBay 应用，复制对应的 API Key。

> `.env` 已加入 `.gitignore`，不会被提交到版本库，请勿将真实 Key 提交到代码仓库。
