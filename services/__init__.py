import json
import random
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import List

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.common.torrent import Torrent
from app.database.models import Code, Actor
from app.database.models.history import History
from app.database.session import session_scope
from app.modules import get_module
from app.settings import get_settings
from app.utils import timer, find_serial_number, get_torrent_hash
from app.utils.log import logger


def is_exist_server(code_no: str):
    module = get_module()
    if module.emby.search(code_no):
        return True
    if module.plex.search(code_no):
        return True
    if module.jellyfin.search(code_no):
        return True
    return False


def search_code(code_no: str):
    module = get_module()
    codes, actors = module.avbase.search_keyword(code_no)
    if codes:
        code = codes[0]
        code.code = code_no
        return code
    code = module.bus.search(code_no)
    if code:
        code.code = code_no
        return code
    code = module.avdb.search(code_no)
    if code:
        code.code = code_no
        return code
    return None


def find_torrent(code: Code, torrents: List[Torrent]):
    logger.info(f"开始过滤{code.code}的资源,订阅模式:{code.mode}")
    settings = get_settings()
    filter_str = code.filter if code.filter else json.dumps(settings.DEFAULT_FILTER)
    sort = settings.DEFAULT_SORT
    filter = json.loads(filter_str)
    logger.info(f"过滤器:{filter}")
    sort_list = sort.split(',')
    logger.info(f"排序:{sort_list}")
    is_pass_filter = False
    pre_torrents = filter_torrents(torrents, filter)
    if pre_torrents:
        is_pass_filter = True
    if code.mode == 'STRICT':
        torrents = filter_torrents(torrents, filter)
        torrents = sort_torrents(torrents, sort_list)
    else:
        if is_pass_filter:
            torrents = sort_torrents(pre_torrents, sort_list)
        else:
            torrents = sort_torrents(torrents, sort_list)
    if not torrents:
        return [], is_pass_filter
    return torrents[0], is_pass_filter


def sort_torrents(torrents: List[Torrent], sort_by=List[str]):
    settings = get_settings()
    if not sort_by:
        sort_by = ['seeders']
    sort_by = reversed(sort_by)
    for sort_key in sort_by:
        if sort_key == '!uhd':
            torrents = sorted(torrents, key=lambda torrent: getattr(torrent, "uhd"))
        elif sort_key == '!uc':
            torrents = sorted(torrents, key=lambda torrent: getattr(torrent, "uc"))
        elif sort_key == 'site':
            if settings.MAIN_SITE:
                torrents = sorted(torrents, key=lambda torrent: torrent.site != settings.MAIN_SITE)
        else:
            torrents = sorted(torrents, key=lambda torrent: getattr(torrent, sort_key), reverse=True)
    return torrents


def filter_torrents(torrents: List[Torrent], filter: dict):
    filter_list = []
    for torrent in torrents:
        size_mb = torrent.size_mb
        if filter.get('max_size'):
            if size_mb and size_mb > float(filter.get('max_size')):
                continue
        if filter.get('min_size'):
            if size_mb and size_mb < float(filter.get('min_size')):
                continue
        if filter.get('only_chinese'):
            if not torrent.chinese:
                continue
        if filter.get('only_uc'):
            if not torrent.uc:
                continue
        if filter.get('only_uhd'):
            if not torrent.uhd:
                continue
        if filter.get('exclude_uhd'):
            if torrent.uhd:
                continue
        if filter.get('exclude_uc'):
            if torrent.uc:
                continue
        if filter.get('only_free'):
            if not torrent.free:
                continue
        filter_list.append(torrent)
    return filter_list


def run_batch_sub(code_no_list: list[str]):
    for code_no in code_no_list:
        run_sub(code_no)
        time.sleep(random.randint(60, 300))


def run_sub(code_no: str):
    logger.info(f"开始搜索种子资源:{code_no}")
    module = get_module()
    settings = get_settings()
    with session_scope() as session:
        code = session.get(Code, code_no)
        torrents = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_mteam = executor.submit(module.mteam.search, code.code)
            future_ptt = executor.submit(module.ptt.search, code.code)
            future_nicept = executor.submit(module.nicept.search, code.code)
            future_sht = executor.submit(module.sht.search, code.code)
            results = []
            for future in [future_mteam, future_ptt, future_nicept, future_sht]:
                try:
                    results.append(future.result())
                except Exception as e:
                    logger.error(f"搜索失败: {str(e)}")
                    results.append([])
        mteam_torrents, ptt_torrents, nicept_torrents, sht_torrents = results
        torrents.extend(mteam_torrents + ptt_torrents + nicept_torrents + sht_torrents)
        logger.info(f"已搜索到{code_no}的种子资源:{torrents}")
        torrent, is_pass_filter = find_torrent(code, torrents)
        if torrent:
            logger.info(f"过滤完成，得到{code_no}的种子资源：{torrent},即将开始下载种子文件")
            torrent_path = None
            if torrent.site == module.mteam.site_name:
                torrent_path = module.mteam.download_seed(torrent)
            elif torrent.site == module.ptt.site_name:
                torrent_path = module.ptt.download_seed(torrent)
            elif torrent.site == module.nicept.site_name:
                torrent_path = module.nicept.download_seed(torrent)
            elif torrent.site == module.sht.site_name:
                torrent_path = torrent.download_url
            if torrent_path:
                if download_torrent(torrent_path):
                    logger.info(f"成功添加{torrent_path}到下载器,订阅完成")
                    if code.mode == 'STRICT':
                        code.status = 'COMPLETE'
                        threading.Thread(target=lambda: send_complete_message(code.banner, code_no, torrent)).start()
                    else:
                        if is_pass_filter:
                            code.status = 'COMPLETE'
                        else:
                            code.mode = 'STRICT'
                            threading.Thread(
                                target=lambda: send_brush_message(code.code, code.title, code.banner)).start()
                    session.commit()
                    session.refresh(code)
                    if not torrent_path.startswith("magnet"):
                        torrent_hash = get_torrent_hash(torrent_path)
                        history = session.get(History, torrent_hash)
                        if not history:
                            history = History(data={
                                'hash': torrent_hash,
                                'code': code_no,
                                'save_path': settings.QBITTORRENT_DOWNLOAD_PATH
                            })
                            session.add(history)
                            session.commit()
                else:
                    logger.error(f"种子文件添加下载失败：{torrent_path}")
            else:
                logger.error(f"种子文件下载失败：{torrent}")


def subscribe_code_by_actor(actor: Actor, session: Session):
    module = get_module()
    settings = get_settings()
    codes, actors = module.avbase.search_actor(actor.name)
    cache_actors(actors, session)
    for code in codes:
        code_no = code.code
        db_code = session.get(Code, code_no)
        if not db_code:
            session.add(code)
            session.flush()
            session.commit()
            session.refresh(code)
        code = session.get(Code, code_no)
        if code and code.casts and code.status == 'UN_SUBSCRIBE' and not is_exist_server(
                code_no=code_no) and code.release_date > actor.limit_date and 'VR' not in code.code:
            cast_list = code.casts.split(',')
            if len(cast_list) <= int(settings.MAX_ACTOR):
                code.status = 'SUBSCRIBE'
                session.flush()
                session.commit()
                session.refresh(code)
                threading.Thread(target=lambda: send_subscribe_message(code.code, code.title, code.banner)).start()
            else:
                logger.info(f"{code_no}演员人数超过{settings.MAX_ACTOR}名,不进行订阅")


def download_torrent(torrent_path):
    settings = get_settings()
    module = get_module()
    tr_success = False
    qb_success = False
    thunder_success = False
    cloud_success = False
    if torrent_path.startswith("magnet"):
        thunder_success = module.thunder.download(torrent_path)
        cloud_success = module.cloud_nas.download_offline(torrent_path)
        if not thunder_success and not cloud_success and module.qbittorrent.client and not settings.CLOUDNAS_URL:
            qb_success = module.qbittorrent.add_torrent_by_magnet(magnet=torrent_path,
                                                                  save_path=settings.QBITTORRENT_DOWNLOAD_PATH,
                                                                  category=settings.QBITTORRENT_CATEGORY,
                                                                  tags="BYTE_MUSE")
        if not thunder_success and not cloud_success and module.transmission.client and not settings.CLOUDNAS_URL:
            tr_success = module.transmission.add_torrent_by_magnet(magnet=torrent_path,
                                                                   save_path=settings.TRANSMISSION_DOWNLOAD_PATH,
                                                                   tags="BYTE_MUSE")
    else:
        if module.qbittorrent.client:
            qb_success = module.qbittorrent.add_torrent(torrent_file_path=torrent_path,
                                                        save_path=settings.QBITTORRENT_DOWNLOAD_PATH,
                                                        category=settings.QBITTORRENT_CATEGORY, tags="BYTE_MUSE")
        if module.transmission.client:
            tr_success = module.transmission.add_torrent(torrent_file_path=torrent_path,
                                                         save_path=settings.TRANSMISSION_DOWNLOAD_PATH,
                                                         tags="BYTE_MUSE")
    return qb_success or tr_success or thunder_success or cloud_success


def send_subscribe_message(code, title, banner):
    module = get_module()
    settings = get_settings()
    module.wechat.send_photo_message(user_ids=settings.WECHAT_TO_USER, title=f"番号{code}已加入订阅列表",
                                     content=title, banner=banner)
    module.telegram.send_photo_message(banner, f"番号{code}已加入订阅列表\n{title}")
    pass


def send_subscribe_actor_message(name, limit_date, photo):
    module = get_module()
    settings = get_settings()
    module.wechat.send_photo_message(user_ids=settings.WECHAT_TO_USER, title=f"演员{name}已加入订阅列表",
                                     content=f"将自动订阅{limit_date}之后的番号", banner=photo)
    module.telegram.send_photo_message(photo,
                                       f"演员{name}已加入订阅列表\n将自动订阅{limit_date}之后的番号")
    pass


def send_complete_message(banner, code_no, torrent: Torrent):
    module = get_module()
    settings = get_settings()
    content = f"""站点：{torrent.site}\n标题: {torrent.title}\n大小: {torrent.size_mb}MB\n做种: {torrent.seeders}
    """
    module.wechat.send_photo_message(user_ids=settings.WECHAT_TO_USER, title=f"番号{code_no}开始下载",
                                     content=content, banner=banner)
    module.telegram.send_photo_message(banner, f"番号{code_no}开始下载\n{content}")
    pass


def send_downloaded_message(torrent_name, save_path, torrent_hash):
    module = get_module()
    settings = get_settings()
    banner = ''
    code_no = ''
    with session_scope() as session:
        history = session.get(History, torrent_hash)
        if history:
            code_no = history.code
            if code_no:
                code = session.get(Code, code_no)
                if code:
                    banner = code.banner
    if not code_no:
        code_no = find_serial_number(torrent_name)
        if not code_no:
            code_no = '未识别'

    module.wechat.send_photo_message(user_ids=settings.WECHAT_TO_USER, title=f"番号{code_no}已完成下载",
                                     content=f"种子名称:{torrent_name}\n保存路径:{save_path}", banner=banner)
    module.telegram.send_photo_message(photo_url=banner,
                                       caption=f"番号{code_no}已完成下载\n种子名称:{torrent_name}\n保存路径:{save_path}")
    pass


def send_brush_message(code, title, banner):
    module = get_module()
    settings = get_settings()
    module.wechat.send_photo_message(user_ids=settings.WECHAT_TO_USER,
                                     title=f"番号{code}已完成初次下载,进入严格模式", content=title, banner=banner)
    module.telegram.send_photo_message(banner, f"番号{code}已完成初次下载,进入严格模式\n{title}")
    pass


def reply_text_msg(channel, msg):
    settings = get_settings()
    module = get_module()
    if channel == 'wx':
        module.wechat.send_text_message(user_ids=settings.WECHAT_TO_USER, content=msg)
    if channel == 'tg':
        module.telegram.send_text_message(text=msg)


@timer(name="推荐接口")
def get_recommend(session: Session):
    # 返回订阅最多的tag，演员，系列
    codes = session.query(Code).filter(Code.status.in_(['SUBSCRIBE', 'COMPLETE'])).all()
    genres_list = []
    cast_list = []
    series_list = []
    publisher_list = []
    weight = {"genres": 0.1, "cast": 0.5, "series": 0.2, "publisher": 0.2}
    for code in codes:
        genres = code.genres
        if genres:
            genres_list.extend(genres.split(','))
        casts = code.casts
        if casts:
            cast_list.extend(casts.split(','))
        series = code.series
        if series:
            series_list.append(series)
        publisher = code.publisher
        if publisher:
            publisher_list.append(publisher)
    genres_count = Counter(genres_list)
    cast_count = Counter(cast_list)
    series_count = Counter(series_list)
    publisher_count = Counter(publisher_list)
    sorted_genres_counted = sorted(genres_count.items(), key=lambda item: item[1], reverse=True)[:10]
    sorted_cast_counted = sorted(cast_count.items(), key=lambda item: item[1], reverse=True)[:10]
    sorted_series_counted = sorted(series_count.items(), key=lambda item: item[1], reverse=True)[:10]
    sorted_publisher_counted = sorted(publisher_count.items(), key=lambda item: item[1], reverse=True)[:10]
    genres_score = {item: 10 - index for index, (item, _) in enumerate(sorted_genres_counted)}
    cast_score = {item: 10 - index for index, (item, _) in enumerate(sorted_cast_counted)}
    series_score = {item: 10 - index for index, (item, _) in enumerate(sorted_series_counted)}
    publisher_score = {item: 10 - index for index, (item, _) in enumerate(sorted_publisher_counted)}
    # 获取当前日期
    current_date = datetime.now()
    previous_month = current_date - relativedelta(months=1)
    next_month = current_date + relativedelta(months=1)
    unsubscribe_codes = session.query(Code).filter(Code.status == 'UN_SUBSCRIBE').filter(
        Code.release_date.between(previous_month.strftime("%Y-%m-%d"), next_month.strftime("%Y-%m-%d"))).all()
    session.close()
    for code in unsubscribe_codes:
        code_weight = 0
        if code.genres:
            for item, score in genres_score.items():
                if item in code.genres:
                    code_weight += score * weight['genres']
        if code.series:
            for item, score in series_score.items():
                if item in code.casts:
                    code_weight += score * weight['series']
        if code.publisher:
            for item, score in publisher_score.items():
                if item in code.publisher:
                    code_weight += score * weight['publisher']
        if code.casts:
            cast_arr = code.casts.split(',')
            if len(cast_arr) <= 3:
                for item, score in cast_score.items():
                    if item in code.casts:
                        code_weight += score * weight['cast']
        setattr(code, "weight", code_weight)
    filtered_data = [item for item in unsubscribe_codes if item.weight > 0]
    recommend_list = sorted(filtered_data, key=lambda item: item.weight, reverse=True)[:48]
    recommend_list = [item for item in recommend_list if not is_exist_server(item.code)]
    return recommend_list


def cache_actors(actors, session: Session):
    if actors:
        for actor in actors:
            db_actor = session.get(Actor, actor.name)
            if not db_actor:
                session.add(actor)
                session.commit()
                session.refresh(actor)
