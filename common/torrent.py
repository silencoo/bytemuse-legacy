from typing import List, Dict

from app.settings import get_settings
from app.utils import dict_trans_obj


class Torrent:
    id: int = 0
    site: str = ""
    size_mb: float = 0
    seeders: int = 0
    title: str = ""
    chinese: bool = False
    uc: bool = False
    uhd: bool = False
    free: bool = False
    download_url: str = ""

    cn_keywords: List[str] = ['中字', '中文字幕', '色花堂', '字幕']
    uc_keywords: List[str] = ['UC', '无码', '步兵']
    uhd_keywords: List[str] = ['4k', '8k', '2160p', '4K', '8K', '2160P']

    def __init__(self, id, site, size_mb, seeders, title, download_url, free):
        self.id = int(id)
        self.site = site
        self.size_mb = size_mb
        self.seeders = seeders
        self.title = title
        self.chinese = self.has_chinese(title)
        self.uc = self.has_uc(title)
        self.uhd = self.has_uhd(title)
        self.free = free
        self.download_url = download_url

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    def has_chinese(self, title: str):
        has_chinese = False
        for keyword in self.cn_keywords:
            if title.find(keyword) > -1:
                has_chinese = True
                break
        return has_chinese

    def has_uc(self, title: str):
        uc = False
        for keyword in self.uc_keywords:
            if title.find(keyword) > -1:
                uc = True
                break
        return uc

    def has_uhd(self, title: str):
        uhd = False
        for keyword in self.uhd_keywords:
            if title.find(keyword) > -1:
                uhd = True
                break
        return uhd

    def __str__(self):
        return f'{self.__class__.__name__}({self.__dict__})'

    def __repr__(self):
        return self.__str__()
