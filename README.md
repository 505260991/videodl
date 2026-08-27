# videodl-youku

Youku-only downloader，支持 Android Termux，并支持持久化 Cookie。

## Termux

    pkg update
    pkg install python ffmpeg git
    git clone https://github.com/505260991/videodl.git
    cd videodl
    pip install -r requirements.txt

### 方式 1：Cookie 文件（推荐）

创建：

    mkdir -p ~/.config/videodl
    nano ~/.config/videodl/youku_cookie.txt

把浏览器获取的 Youku Cookie 字符串放进去：

    a=b; c=d; ...

然后：

    python -m videodl.videodl -i "https://v.youku.com/..."

### 方式 2：命令行

    python -m videodl.videodl -i "https://v.youku.com/..." -c "a=b; c=d"

### 方式 3：环境变量

    export YOUKU_COOKIE='a=b; c=d'
    python -m videodl.videodl -i "https://v.youku.com/..."

Cookie 会同时用于 Python 解析请求和 FFmpeg 下载请求。

## 依赖

Python 3.10+、requests、系统 ffmpeg。

本项目不绕过 DRM；如果 Youku 返回 DRM 或账号无权访问的流，程序不会尝试破解。
