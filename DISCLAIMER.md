# 免责声明 / Disclaimer

**最后更新：2026-10-23**

## 中文

### 1. 非官方、无关联、未获授权

本项目（下称"本工具"）是个人编写的浏览器自动化脚本，**与豆包、字节跳动、火山引擎及其关联公司没有任何关系**，未获其授权、认可或技术支持，也不代表其立场。文中出现的"豆包""Doubao""火山方舟""Volcengine"等名称仅用于说明兼容对象，相关商标归其各自权利人所有。

### 2. 是界面自动化，不是 API

本工具通过模拟人在网页上的操作来读写豆包页面，**不是官方 API**，不具备 API 应有的稳定性、并发能力、流式输出与服务等级承诺。豆包前端的任何一次改版（DOM 结构、class 名、`data-testid`、编辑器框架）都可能让本工具立即失效，且不保证修复。

### 3. 账号风险由使用者自行承担

自动化访问网页服务**可能构成对《豆包用户协议》及相关服务条款的违反**。由此可能导致的后果包括但不限于：请求被限流、功能被限制、账号被冻结或永久封禁、对话记录异常。**这些风险与后果完全由使用者自行承担，作者不承担任何责任，也不提供任何形式的补偿。** 使用前请自行阅读并评估你是否接受该风险。

### 4. 只用你自己的额度

本工具**只调用使用者本人已登录、已获授权的账号额度**：

- 不绕过任何登录、鉴权或计费机制
- 不包含任何破解、逆向、注入、越权或"白嫖"第三方账号的手段
- 不提供、不代充、不共享、不出售任何账号、额度或 API Key
- 不得将他人账号、他人登录态用于本工具

### 5. 禁止用途

禁止将本工具用于：

- 商业转售、代客刷量、按次收费的对外服务
- 大规模批量抓取、爬取或囤积生成内容
- 生成、传播违反法律法规或侵犯他人权益的内容
- 规避平台风控、限流、内容审核，或任何打码、绕过的用途
- 冒充官方服务，或让第三方误以为这是官方提供的接口

### 6. 合规责任

使用者应自行确认其使用行为符合所在国家或地区的法律法规、以及豆包/火山引擎的服务条款。**如官方对本项目提出异议，请立即停止使用并删除本项目的全部副本。**

### 7. 无担保

本软件按**「现状」（AS IS）**提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性与不侵权担保。作者不保证其正确性、可用性、不中断或无错误。

### 8. 责任限制

在适用法律允许的最大范围内，**对于因使用或无法使用本工具而产生的任何直接、间接、偶然、特殊或后果性损失**（包括但不限于账号损失、数据丢失、业务中断、利润损失、第三方索赔），**作者均不承担任何责任**。是否使用、如何使用，完全由使用者自主决定并自担风险。

### 9. 许可

代码以 [MIT License](LICENSE) 发布。MIT 许可中的免责条款与本文件共同构成完整的免责约定；本文件与 MIT 许可冲突时，以更严格的一方为准。

---

## English (Summary)

This project is an **unofficial, personal browser-automation script**. It is **not affiliated with, endorsed by, or authorized by Doubao, ByteDance, or Volcano Engine**. It drives the Doubao web UI the way a human would and is **not an official API** — it has no streaming, no concurrency, no SLA, and will break whenever the site changes.

Automated access **may violate Doubao's Terms of Service**. Rate limiting, feature restrictions, account suspension or permanent bans are **entirely at your own risk**. The author accepts no liability of any kind.

The tool only uses **your own logged-in, authorized account quota**. It contains no cracking, bypassing, or authentication-evasion code, and it does not provide, share, or sell accounts, quota, or API keys. Do not use it for resale, bulk scraping, evading platform risk controls, or generating unlawful content.

The software is provided **"AS IS"**, without warranty of any kind, express or implied. To the maximum extent permitted by law, the author shall not be liable for any direct, indirect, incidental, special, or consequential damages arising from the use of, or inability to use, this software.

If the official provider objects to this project, stop using it and delete all copies immediately.
