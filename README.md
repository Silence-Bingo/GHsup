# GitHub 加速器

通过修改 hosts 文件加速 GitHub 访问，解决 DNS 污染问题。

## 功能特点

- 🔍 使用多个公共 DNS 服务器（Cloudflare、Google、阿里、腾讯等）解析 GitHub 域名
- ⚡ 自动测试 IP 延迟，选择最快的 IP
- 🔄 每小时自动刷新 IP 地址
- 📝 自动备份 hosts 文件
- 🖥️ 图形界面 + 系统托盘
- ☁️ 支持 Cloudflare Worker 作为 DNS 代理

## 加速的域名

- github.com
- github.global.ssl.fastly.net
- assets-cdn.github.com
- raw.githubusercontent.com
- gist.githubusercontent.com
- codeload.github.com
- api.github.com

## 使用方法

### 方法一：直接运行（Windows）

1. 下载 `GitHub加速器.exe`
2. 右键以管理员身份运行
3. 点击"立即加速"按钮

### 方法二：从源码运行

```bash
# 安装依赖
pip install -r requirements.txt

# 图形界面模式
python main.py --gui

# 命令行模式
python main.py

# 后台模式（每小时自动刷新）
python main.py --daemon

# 禁用加速
python main.py --disable
```

### 方法三：打包为 EXE

**Windows 本地打包：**

```cmd
build.bat
```

**GitHub Actions 自动打包（推荐）：**

1. Fork 或上传项目到 GitHub
2. 推送到 main 分支后自动触发打包
3. 进入仓库的 Actions 页面 → 点击最新的 workflow run
4. 在 Artifacts 区域下载 `GitHub加速器.zip`
5. 解压后得到 `GitHub加速器.exe`

## 配置 Cloudflare Worker（可选）

Cloudflare Worker 可以作为 DNS 代理，在网络受限时提供更可靠的 DNS 解析。

### 部署步骤

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 Workers & Pages
3. 创建新的 Worker
4. 复制 `cloudflare-worker/worker.js` 的内容
5. 保存并部署
6. 记录 Worker URL（如 `https://your-worker.workers.dev`）

### 使用 Worker

启动程序时添加 `--cf-worker` 参数：

```bash
python main.py --cf-worker https://your-worker.workers.dev
```

或在 GUI 中修改配置文件 `~/.github-accelerator/config.json`：

```json
{
  "cf_worker_url": "https://your-worker.workers.dev"
}
```

## 配置文件

配置文件位于 `~/.github-accelerator/config.json`：

```json
{
  "cf_worker_url": "",
  "auto_refresh": true,
  "refresh_interval": 3600,
  "last_update": "2024-01-01T00:00:00",
  "last_ips": {
    "github.com": "140.82.121.3",
    "raw.githubusercontent.com": "185.199.108.133"
  }
}
```

## Hosts 文件位置

- Windows: `C:\Windows\System32\drivers\etc\hosts`
- Linux/Mac: `/etc/hosts`

备份文件位于 hosts 文件同目录下的 `hosts_backups` 文件夹。

## 注意事项

1. **需要管理员权限**：修改 hosts 文件需要管理员/root 权限
2. **自动备份**：每次更新前会自动备份原 hosts 文件
3. **标记机制**：使用特殊注释标记加速器添加的内容，方便识别和移除
4. **禁用加速**：运行 `python main.py --disable` 或点击 GUI 中的"禁用加速"按钮

## 许可证

MIT License
