# rag-qa

<!-- TODO（步骤 1 之前定）：一句话说明 —— 它能回答【什么文档】的问题？ -->

> 🚧 开发中

## 技术栈

- 先读文档，再切块      → pypdf          （把 PDF 里的文字读出来）
- 存向量                → chromadb
- 调模型生成回答         → openai + python-dotenv   （调 DeepSeek，Key 从 .env 读）
- 网页界面              → streamlit



## 快速开始
把仓库下载下来，然后进到那个文件夹里
```
git clone <仓库地址>
cd rag-qa
```
建立一个自己的venv环境（文件名必须为.venv防止被上传到github里面）
```
python -m venv .venv
```
激活venv环境
```
.\.venv\Scripts\Activate.ps1
```
根据requirements.txt安装所需要的包
```
pip install -r requirements.txt
```
根据.env.example文件复制成.env文件
```
Copy-Item .env.example .env
```
并在文件里面填写自己的api key
