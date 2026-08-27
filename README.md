# videodl-youku

Youku-only 精简版。保留原项目 Youku 的核心解析流程：从 Youku URL 提取 vid，访问 log.mmstat.com 获取 utid，再调用 ups.youku.com/ups/get.json，过滤 tail 流并按 height、width、size 降序选择最高质量 m3u8。

## Android Termux

    pkg update
    pkg install python ffmpeg git
    git clone https://github.com/505260991/videodl.git
    cd videodl
    pip install -r requirements.txt

下载：

    python -m videodl.videodl -i "https://v.youku.com/v_show/id_XXXX.html"

或者：

    python -m videodl.videodl "https://v.youku.com/v_show/id_XXXX.html"

安装命令后也可以：

    pip install -e .
    videodl -i "https://v.youku.com/v_show/id_XXXX.html"

## 依赖

Python 3.10+、requests、系统 ffmpeg。已移除其他平台、CDM、Node.js、curl-cffi、m3u8、rich、fake-useragent 等非 Youku 依赖。

## 说明

Youku 接口、地区限制、登录权限或 DRM 可能导致特定视频无法取得可播放 m3u8。本项目不绕过 DRM，只处理 Youku 接口返回的可播放流。
