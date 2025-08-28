# Markdown Quiz Generator

## 🚀 快速开始

### 独立使用Flask服务

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

详细集成说明请查看：[DIFY_INTEGRATION.md](DIFY_INTEGRATION.md)

## 🔧 配置外部访问地址

### Docker Compose 部署时的重要配置

当通过 Docker Compose 部署时，为了确保生成的试卷链接能在浏览器端正常访问，需要正确配置服务的外部访问地址：

#### 方法一：环境变量配置（推荐）

在 `docker-compose.yaml` 中设置环境变量：

```yaml
quiz-flask-service:
  environment:
    QUIZ_SERVICE_HOST: localhost  # 改为你的服务器IP或域名
    QUIZ_SERVICE_PORT: 5006
    QUIZ_SERVICE_PROTOCOL: http
```

#### 方法二：使用 .env 文件

创建 `.env` 文件：

```bash
# 本地开发环境
QUIZ_SERVICE_HOST=localhost

# 生产环境示例
# QUIZ_SERVICE_HOST=yourdomain.com
# QUIZ_SERVICE_HOST=192.168.1.100

QUIZ_SERVICE_PORT=5006
QUIZ_SERVICE_PROTOCOL=http
```

#### 配置说明：

- **本地开发**: `QUIZ_SERVICE_HOST=localhost`
- **局域网访问**: `QUIZ_SERVICE_HOST=192.168.1.100` (你的服务器IP)
- **公网访问**: `QUIZ_SERVICE_HOST=yourdomain.com` (你的域名)

### 重启服务

配置修改后，重启服务使配置生效：

```bash
docker-compose down
docker-compose up -d quiz-flask-service
```

---

### Introduction
It is a tool to generate quizzes from Markdown files. This means that you can structure the format of the text, bold, italic, tables, etc.

<b> Markdown: </b> <br>
![p1](https://raw.githubusercontent.com/osandadeshan/markdown-quiz-generator/master/app/static/sample-quiz-md-file.PNG)

<b> Quiz generated: </b> <br>
![p2](https://raw.githubusercontent.com/osandadeshan/markdown-quiz-generator/master/app/static/sample-quiz-animation.gif)

### Requirements
install.bat - automatically download and install all requirements and dependencies <br> ([Python-3.12.x](https://www.python.org/), [pip](https://pypi.org/project/pip/) )

### Manual Installation
Once `python` and `pip` are installed, simply run (within the application already downloaded): <br>
`python -m pip install -r requirements.txt`

### Quiz structure (Markdown)
Although it is based on markdown for its style format, at the moment the following types of questions are supported:

1. **Question of a selection**:
```text
1. MaxSoft is a software company.
    - (x) True
    - ( ) False
```
```text
2. The domain of MaxSoft is test automation framework development.
    - (x) True
    - ( ) False 
```
Note that the correct answer is specified with an **x** ( x or X, upper or lower case) and must be in parentheses to specify that it is only one to be selected, for example, for false or true questions.

2. **Multiple selection question**:
```text
3. What are the test automation frameworks developed by MaxSoft?
    - [x] IntelliAPI
    - [x] WebBot
    - [ ] Gauge
    - [ ] Selenium
```
Very similar to the previous one but this type of question allows you to select more than one at a time, they must be in square brackets with an **x** to the correct answers. The result to these types of questions is prorated, that is, you must select only the correct ones so that that question is interpreted as correct.

Note that for questions types 1 and 2, you must leave a space for the wrong answers, eg. () or [], the questions must be multiple selection or a selection, you cannot mix them.

3. **Open question** (Enter text)
```text
4. Who is the Co-Founder of MaxSoft?
    - R:= Osanda
```
It is a question where you must write the correct answer, this is specified in the following line of the question preceded by **R: =** (R or, upper or lower case) then the correct answer (it is validated regardless of whether it is uppercase or lowercase)

### Designing the quiz
There are several tools out there on the internet that allow you to preview Markdown files. 
Some online examples:

1. https://dillinger.io/
2. https://markdownlivepreview.com/

### Generating quizzes
The application will generate all the **.md** (Markdown) files that are inside the folder 
`./markdown-quiz-files/**`. Note that this folder already has a default quiz (sample-quiz.md).

You can add as many as Markdown files you want, and each of them will be generated separate quizzes.

To generate quizzes, there are two batch files,
1. `quiz-generator-local.bat` \
This is a batch file that simply executes `python quiz-generator.py` and will generate the quizzes including the required libraries (Bootstrap, jQuery) to execute it independently in the browser (usually to verify that everything is fine).

2. `quiz-generator-local-server.bat` \
This is a batch file that executes, 
```
python quiz-generator.py
cd docs
start http://localhost:8000/
python -m http.server 8000
```
This is almost same as `quiz-generator-local.bat`. The only difference is, this will spin up a new local server for your quizzes at http://localhost:8000/

3. `quiz-generator-embed.bat` \
This is a batch file that simply executes `python quiz-generator.py embed` in this way the quizzes will be generated without including any external library, it is assumed that it will be included in another Web as (Embedded).

The resulting quizzes will have the same name of the markdown file but with their .html extension, they will be created in the `./docs/` folder.

### Deploy GitHub Pages

Deploy the `/docs/` directory to GitHub pages to serve publicly on the web. After creating a quiz in the `/docs/` directory, add a link to the `/docs/index.html` file.

![add link to new quiz](./app/static/add-links-to-index.png)

Go to Settings in your GitHub repository. Select **Pages** on the left navigation bar.  Select **Deploy from a Branch**.  Then select the **docs** directory to deploy from.

![deploy from docs directory](./app/static/deploy-to-github-pages.png)

Once you've set up GitHub Pages, you can navigate to **Actions** and follow the progress of the deployment.  If the deployment is successful, you'll see the green dot as show below.

![check deployment process](./app/static/github-actions.png)

Return to **Settings/Pages** to find the link to the deployed web site.

![visit deployed website](./app/static/ghpages-visit-site.png)

The **index.html** will provide links to available quizzes.

![deployed website](./app/static/deployed-website.png)
