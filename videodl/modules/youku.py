import os
import random
import re
import string
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import requests

YOUKU_SUFFIXES = {'youku.com','www.youku.com','v.youku.com','m.youku.com','player.youku.com','vku.youku.com'}
DEFAULT_COOKIE_FILE = Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config')) / 'videodl' / 'youku_cookie.txt'

def legalize(name):
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', str(name or 'video'))
    return re.sub(r'\s+', ' ', name).strip().rstrip('.') or 'video'

def parse_cookie_string(value):
    cookies = {}
    for part in (value or '').split(';'):
        part = part.strip()
        if '=' in part:
            k, v = part.split('=', 1)
            k = k.strip()
            if k:
                cookies[k] = v.strip()
    return cookies

def load_cookie_file(path=None):
    p = Path(path or DEFAULT_COOKIE_FILE).expanduser()
    if not p.is_file():
        return {}
    text = p.read_text(encoding='utf-8').strip()
    if not text:
        return {}
    # Accept both "a=b; c=d" and one "a=b" per line.
    return parse_cookie_string(text.replace('\n', ';'))

def safeget(obj, path, default=None):
    cur = obj
    for key in path:
        if isinstance(cur, dict): cur = cur.get(key, default)
        elif isinstance(cur, list) and isinstance(key, int) and 0 <= key < len(cur): cur = cur[key]
        else: return default
    return cur

@dataclass
class VideoInfo:
    source: str
    download_url: str = ''
    title: str = 'video'
    save_path: str = ''
    ext: str = 'mp4'
    identifier: str = ''
    cover_url: str | None = None
    raw_data: dict = field(default_factory=dict)
    err_msg: str | None = None
    download_with_ffmpeg: bool = True
    @property
    def with_valid_download_url(self): return bool(self.download_url)

class BaseVideoClient:
    source = 'BaseVideoClient'
    def __init__(self, max_retries=5, work_dir='videodl_outputs',
                 default_parse_cookies=None, default_download_cookies=None,
                 default_parse_headers=None, default_download_headers=None,
                 disable_print=False, **_):
        self.max_retries = max(1, int(max_retries))
        self.work_dir = work_dir
        self.disable_print = disable_print
        self.default_parse_cookies = dict(default_parse_cookies or {})
        self.default_download_cookies = dict(default_download_cookies or {})
        self.default_parse_headers = dict(default_parse_headers or {})
        self.default_download_headers = dict(default_download_headers or {})
        self.default_headers = self.default_parse_headers
        self.session = requests.Session()
        self.session.headers.update(self.default_headers)
        Path(work_dir).mkdir(parents=True, exist_ok=True)

    def get(self, url, **kwargs):
        headers = dict(self.default_headers)
        headers.update(kwargs.pop('headers', {}) or {})
        cookies = dict(self.default_parse_cookies)
        cookies.update(kwargs.pop('cookies', {}) or {})
        for attempt in range(self.max_retries):
            try: return self.session.get(url, headers=headers, cookies=cookies, timeout=30, **kwargs)
            except Exception:
                if attempt + 1 == self.max_retries: raise
                time.sleep(min(2 ** attempt, 5))

    def _unique(self, path):
        p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists(): return p
        for i in range(1, 10000):
            q = p.with_name(f'{p.stem} ({i}){p.suffix}')
            if not q.exists(): return q
        raise RuntimeError('cannot create unique output path')

    def download(self, video_infos, num_threadings=1, request_overrides=None):
        done = []
        for info in video_infos:
            if not info.with_valid_download_url: continue
            try:
                out = self._unique(info.save_path); info.save_path = str(out)
                headers = dict(self.default_download_headers)
                headers.update((request_overrides or {}).get('headers', {}) or {})
                header_text = ''.join(f'{k}: {v}\r\n' for k, v in headers.items())
                cookie_text = '; '.join(f'{k}={v}' for k, v in self.default_download_cookies.items())
                cmd = ['ffmpeg','-hide_banner','-loglevel','error','-y']
                if header_text: cmd += ['-headers', header_text]
                if cookie_text: cmd += ['-cookies', cookie_text]
                cmd += ['-i', info.download_url, '-c', 'copy', '-movflags', '+faststart', str(out)]
                subprocess.run(cmd, check=True)
                done.append(info)
                if not self.disable_print: print(f'Downloaded: {out}')
            except Exception as exc:
                info.err_msg = f'{self.source}.download >>> {info.identifier} (Error: {exc})'
                if not self.disable_print: print(info.err_msg)
        return done

class YoukuVideoClient(BaseVideoClient):
    source = 'YoukuVideoClient'
    def __init__(self, cookie=None, cookie_file=None, **kwargs):
        self.cookie_file = Path(cookie_file or DEFAULT_COOKIE_FILE).expanduser()
        supplied = cookie or os.environ.get('YOUKU_COOKIE') or ''
        cookies = parse_cookie_string(supplied) if supplied else load_cookie_file(self.cookie_file)
        super().__init__(default_parse_cookies=cookies, default_download_cookies=cookies, **kwargs)
        self.default_parse_headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'}
        self.default_download_headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}
        self.default_headers = self.default_parse_headers
        self._initsession()

    def _initsession(self): self.session.headers.update(self.default_headers)

    def _getformatname(self, fm):
        return {'3gp':'h6','3gphd':'h5','flv':'h4','flvhd':'h4','mp4':'h3','mp4hd':'h3','mp4hd2':'h4','mp4hd3':'h4','hd2':'h2','hd3':'h1'}.get(fm)

    @staticmethod
    def belongto(url, valid_domains=None):
        return BaseVideoClient.belongto(url, set(valid_domains or []) | YOUKU_SUFFIXES)

    def parsefromurl(self, url, request_overrides=None):
        info = VideoInfo(source=self.source)
        try:
            if not self.belongto(url): return []
            try: vid = parse_qs(urlparse(url).query, keep_blank_values=True)['vid'][0]
            except Exception:
                vid = urlparse(url).path.strip('/').split('/')[-1]
                if vid.endswith('.html'): vid = vid[:-5]
                if vid.startswith('id_'): vid = vid[3:]
            if not self.default_parse_cookies:
                raise RuntimeError(f'Youku Cookie is required. Put it in {self.cookie_file} or set YOUKU_COOKIE.')
            overrides = dict(request_overrides or {})
            resp = self.get('https://log.mmstat.com/eg.js', **overrides); resp.raise_for_status()
            utid = (resp.headers.get('ETag') or resp.headers.get('etag') or '').strip('"')
            params = {'vid':vid,'ccode':'0564','client_ip':'192.168.1.1','utid':utid,'client_ts':int(time.time())}
            headers = dict(self.default_headers); headers['Referer'] = url
            resp = self.get('https://ups.youku.com/ups/get.json', params=params, headers=headers, **overrides); resp.raise_for_status()
            raw = resp.json(); data = raw.get('data') or {}
            streams = []
            for s in data.get('stream', []):
                if isinstance(s, dict) and s.get('channel_type') != 'tail' and s.get('m3u8_url'):
                    streams.append((int(s.get('height',0) or 0),int(s.get('width',0) or 0),int(s.get('size',0) or 0),s['m3u8_url']))
            streams.sort(reverse=True)
            if not streams: raise RuntimeError('Youku did not return a playable m3u8 stream')
            info.download_url=streams[0][3]; info.title=legalize(safeget(data,['video','title'],'video')); info.identifier=vid
            info.cover_url=safeget(raw,['data','video','logo']) or safeget(raw,['data','preview','thumb_hd',0])
            info.raw_data=raw; info.save_path=os.path.join(self.work_dir,self.source,f'{info.title}.mp4')
        except Exception as exc:
            info.err_msg=f'{self.source}.parsefromurl >>> {url} (Error: {exc})'
            if not self.disable_print: print(info.err_msg)
        return [info]

__all__=['BaseVideoClient','YoukuVideoClient','VideoInfo','parse_cookie_string','load_cookie_file']
