# V2Nodes 配置抓取并上传到 GitHub Gist

## 项目介绍

该项目提供一个 Python 脚本，用于从 **V2Nodes** 网站抓取服务器配置信息，并将这些配置信息上传到 **GitHub Gist**。该脚本支持自动抓取多个页面上的服务器配置，并将抓取到的数据上传到 GitHub Gist，方便后续查看或分享。

## 如何在 GitHub Actions 中使用

本指南将介绍如何在 GitHub Actions 中使用该项目，包括以下几个步骤：

1. **Fork 本项目**
2. **生成 GitHub Token**
3. **在 Gist 中设置配置并获取 Gist ID**
4. **设置 GitHub Token 和其他环境变量**
5. **触发 Actions 运行**

---

### 1. Fork 本项目

1. 打开项目的 GitHub 仓库页面。
2. 点击右上角的 **Fork** 按钮，将该项目复制到你自己的 GitHub 账户下。

---

### 2. 生成 GitHub Token

在开始之前，你需要生成一个 GitHub 个人访问令牌（**Personal Access Token**，简称 **PAT**）。这个令牌将用于在 GitHub API 中进行身份验证。以下是生成 Token 的步骤：

1. 登录到 GitHub。
2. 进入 [GitHub Personal Access Tokens 页面](https://github.com/settings/tokens)。
3. 点击 **Generate new token**。
4. 在 **Note** 中填写 Token 名称，例如 "V2Nodes Token"。
5. 在 **Select scopes**（选择权限）部分，选择以下权限：
   - **repo**：允许访问和管理私有仓库（如果你有私有仓库或私有 Gist）。
   - **gist**：Gist必须给予读写权限（必须选择此权限来上传配置到 Gist）。
6. 生成 Token 后，复制该 Token（请妥善保管，因为页面关闭后无法再次查看）。

---

### 3. 在 Gist 中设置配置并获取 Gist ID

如果你希望将抓取的配置上传到一个已有的 Gist，你需要先创建一个公开的 Gist。以下是步骤：

1. 访问 [GitHub Gist 页面](https://gist.github.com/)。
2. 点击 **New gist** 创建一个新的 Gist。名称必须为V2Nodes_config.txt，否则就要更改main.py里的文件名。
3. 在 **Visibility**（可见性）部分，确保选择 **Public**（公开）。如果设置为私有，脚本将无法上传配置。
4. 创建完 Gist 后，获取该 Gist 的 ID。Gist 的 URL 格式为 `https://gist.github.com/username/gist_id`，其中 `gist_id` 就是你需要的 Gist ID。
   - 例如，Gist URL 为 `https://gist.github.com/username/abcdef1234567890`，则 `abcdef1234567890` 就是你的 Gist ID。
5. 将 Gist ID 记录下来，后续将在环境变量中使用。

---

### 4. 设置 GitHub Token 和其他环境变量

在 GitHub Actions 中，你需要设置一些环境变量来传递配置。以下是需要设置的环境变量：

- `MY_GITHUB_TOKEN`：你刚刚生成的 GitHub 个人访问令牌，用于认证 API 请求。
- `MY_GIST_ID`：你要上传配置的 GitHub Gist ID。

#### 如何添加环境变量：

1. 打开你的 GitHub 仓库。
2. 进入 **Settings**（设置） > **Secrets and variables** > **Actions**。
3. 点击 **New repository secret**，分别添加如下两个 Secret：
   - `MY_GITHUB_TOKEN`：粘贴你生成的 GitHub Token。
   - `MY_GIST_ID`（可选）：如果你希望上传到现有的 Gist，可以添加该变量。如果没有该 ID，脚本会自动创建新的 Gist。

---

### 5. 触发 Actions 运行

1. 每当你推送代码到 `main` 分支时，GitHub Actions 会自动运行该工作流。
2. 如果你希望手动触发工作流，也可以在 GitHub 仓库页面的 **Actions** 标签下，点击相应的工作流，然后点击 **Run workflow** 按钮手动触发。

---
## 脚本运行输出

- 如果配置抓取和上传成功，GitHub Actions 会输出类似以下的信息：

```bash
正在抓取页面: https://zh.v2nodes.com/?page=1
正在抓取服务器: https://zh.v2nodes.com/servers/12345/
config内容...
未能提取配置： https://zh.v2nodes.com/servers/12345/
正在抓取页面: https://zh.v2nodes.com/?page=2
...
配置信息已上传到 GitHub Gist: https://gist.github.com/your_gist_id
```

---

## 使用方法

访问 [GitHub Gist 页面](https://gist.github.com/)，并找到配置信息上传的文件。

![image1](https://github.com/user-attachments/assets/bd375e76-b1d9-4963-87a1-c622a8d37f28)
![image2](https://github.com/user-attachments/assets/9e927fd0-0e12-4358-a837-6598b424830e)
