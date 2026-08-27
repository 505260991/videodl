import argparse
from .modules.youku import YoukuVideoClient

def main():
    p = argparse.ArgumentParser(description='Youku-only downloader for Termux')
    p.add_argument('-i', '--index-url', '--index_url', dest='url')
    p.add_argument('-o', '--output', default='videodl_outputs')
    a = p.parse_args()
    url = a.url or input('Youku URL: ').strip()
    if not url:
        p.error('Youku URL is required')
    c = YoukuVideoClient(work_dir=a.output)
    infos = c.parsefromurl(url)
    if not infos or not infos[0].with_valid_download_url:
        raise SystemExit(infos[0].err_msg if infos else 'Unable to parse Youku URL')
    c.download(infos)

if __name__ == '__main__':
    main()
