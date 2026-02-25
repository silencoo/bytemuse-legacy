import json
import os
import random
import threading
import traceback
from datetime import datetime, timedelta

import requests
import time

from sqlalchemy.sql.operators import isnot

from app import services, utils
from app.database.models import Code, Actor, Cache
from app.database.session import session_scope
from app.modules import get_module
from app.settings import temp_folder, get_settings
from app.utils import get_filename_from_url, check_file_exists
from app.utils.log import logger
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger


def sub_rank():
    settings = get_settings()
    library_rank = get_library_rank()
    avdb_rank = get_avdb_rank()
    brands_rank = get_brands_rank()
    rank = list(set(library_rank + avdb_rank + brands_rank))
    with session_scope() as session:
        for code_no in rank:
            code = session.get(Code, code_no)
            if code:
                if code.status == 'UN_SUBSCRIBE':
                    code.filter = json.dumps(settings.DEFAULT_FILTER)
                    code.status = 'SUBSCRIBE'
                    if services.is_exist_server(code_no):
                        logger.info(f"{code.code}已存在服务器，自动标记为完成")
                        code.status = 'COMPLETE'
                    if code.status == 'SUBSCRIBE':
                        threading.Thread(target=lambda: services.send_subscribe_message(code.code, code.title,
                                                                                        code.banner)).start()
                    session.commit()
                    session.refresh(code)
            else:
                code = services.search_code(code_no)
                if code:
                    code.filter = json.dumps(settings.DEFAULT_FILTER)
                    code.status = 'SUBSCRIBE'
                    if services.is_exist_server(code_no):
                        logger.info(f"{code.code}已存在服务器，自动标记为完成")
                        code.status = 'COMPLETE'
                    if code.status == 'SUBSCRIBE':
                        threading.Thread(target=lambda: services.send_subscribe_message(code.code, code.title,
                                                                                        code.banner)).start()
                        session.add(code)
                        session.commit()
                        session.refresh(code)
    download_un_exist_photo()


def get_library_rank():
    settings = get_settings()
    module = get_module()
    ranks = []
    if settings.RANK_PAGE and int(settings.RANK_PAGE) > 0:
        with session_scope() as session:
            for i in range(1, int(settings.RANK_PAGE) + 1):
                rank = module.library.crawling_top20(i)
                if not rank:
                    time.sleep(random.randint(1, 600))
                    rank = module.shared.get_shared_rank(i)
                if rank:
                    ranks.extend(rank)
                    rank_cache = Cache({"namespace": 'rank', "key": str(i), "content": ','.join(rank)})
                    session.add(rank_cache)
                    session.commit()
    return ranks


def get_avdb_rank():
    settings = get_settings()
    module = get_module()
    ranks = []
    if settings.RANK_TYPE and settings.RANK_TYPE:
        rank_types = settings.RANK_TYPE.split(',')
        with session_scope() as session:
            for rank_type in rank_types:
                if rank_type in ['daily', 'weekly', 'monthly']:
                    rank = module.avdb.crawling_top(settings.RANK_TYPE)
                    if not rank:
                        time.sleep(random.randint(1, 600))
                        rank = module.shared.get_shared_rank(settings.RANK_TYPE)
                    if rank:
                        rank_cache = Cache({"namespace": 'rank', "key": settings.RANK_TYPE, "content": ','.join(rank)})
                        session.add(rank_cache)
                        session.commit()
                        ranks.extend(rank)
    return ranks


def get_brands_rank():
    settings = get_settings()
    module = get_module()
    ranks = []
    if settings.BRAND_TYPE and settings.BRAND_TYPE:
        brand_types = settings.BRAND_TYPE.split(',')
        with session_scope() as session:
            for brand_type in brand_types:
                if any(brand_type.startswith(prefix) for prefix in
                       ['s1-', 'ip-', 'moodyz-', 'das-', 'madonna-', 'premium-', 'honnaka-', 'attackers-', 'wanz-']):
                    rank = module.brands.get_date_rank(brand_type)
                    if not rank:
                        time.sleep(random.randint(1, 600))
                        rank = module.shared.get_shared_rank(brand_type)
                    if rank:
                        ranks.extend(rank)
                        rank_cache = Cache({"namespace": 'rank', "key": brand_type, "content": ','.join(rank)})
                        session.add(rank_cache)
                        session.commit()
    return ranks


def sync_rank():
    module = get_module()
    logger.info("开始同步榜单数据")
    with session_scope() as session:
        ranks = []
        for i in range(1, 6):
            rank = module.library.crawling_top20(i)
            if not rank:
                time.sleep(random.randint(1, 600))
                rank = module.shared.get_shared_rank(i)
            if rank:
                ranks.extend(rank)
                rank_cache = Cache({"namespace": 'rank', "key": str(i), "content": ','.join(rank)})
                session.add(rank_cache)
                session.commit()
        for rank_type in ['daily', 'weekly', 'monthly']:
            rank = module.avdb.crawling_top(rank_type)
            if not rank:
                time.sleep(random.randint(1, 600))
                rank = module.shared.get_shared_rank(rank_type)
            if rank:
                ranks.extend(rank)
                rank_cache = Cache({"namespace": 'rank', "key": rank_type, "content": ','.join(rank)})
                session.add(rank_cache)
                session.commit()
        for rank_type in ['s1-0', 's1-1', 's1-2', 's1-3', 's1-4', 'ip-0', 'ip-1', 'ip-2', 'ip-3', 'ip-4']:
            rank = module.brands.get_date_rank(rank_type)
            if not rank:
                time.sleep(random.randint(1, 600))
                rank = module.shared.get_shared_rank(rank_type)
            if rank:
                ranks.extend(rank)
                rank_cache = Cache({"namespace": 'rank', "key": rank_type, "content": ','.join(rank)})
                session.add(rank_cache)
                session.commit()
        actor_rank = module.library.crawling_top20_actor()
        if not actor_rank:
            time.sleep(random.randint(1, 600))
            actor_rank = module.shared.get_shared_rank("actors")
        if actor_rank:
            rank_cache = Cache({"namespace": 'rank', "key": "actors", "content": ','.join(actor_rank)})
            session.add(rank_cache)
            session.commit()
            for actor in actor_rank:
                db_actor = session.get(Actor, actor)
                if not db_actor:
                    codes, actors = module.avbase.search_actor(actor)
                    services.cache_actors(actors, session)
        for code_no in set(ranks):
            db_code = session.get(Code, code_no)
            if not db_code:
                code = services.search_code(code_no)
                if code:
                    session.add(code)
                    session.flush()
                    session.commit()
                    session.refresh(code)
        download_un_exist_photo()


def run_news():
    module = get_module()
    logger.info("开始同步今日上新")
    with session_scope() as session:
        codes = module.avbase.work_date(date=datetime.now().strftime('%Y-%m-%d'))
        for code in codes:
            code_no = code.code
            db_code = session.get(Code, code_no)
            if not db_code:
                session.add(code)
                session.commit()


def download_un_exist_photo():
    logger.info("开始补充未下载的图片")
    settings = get_settings()
    proxies = {
        "http": settings.PROXY,
        "https": settings.PROXY
    }
    headers = {
        'Referer': 'https://www.javbus.com/'
    }
    with session_scope() as session:
        codes = session.query(Code).all()
        for code in codes:
            try:
                if code.banner:
                    filename = get_filename_from_url(code.banner)
                    filepath = os.path.join(temp_folder, filename)
                    if not check_file_exists(temp_folder, filename):
                        protocol, domain = utils.get_protocol_and_domain(code.banner)
                        if domain == 'www.javbus.com':
                            response = requests.get(code.banner, proxies=proxies, headers=headers, timeout=10)
                            if response.ok:
                                with open(filepath, 'wb') as out_file:
                                    out_file.write(response.content)
            except Exception as e:
                logger.error(f"下载番号{code.code}的图片失败: {e}")


def run_codes():
    one_week_later = datetime.now().date() + timedelta(days=7)
    with session_scope() as session:
        codes = session.query(Code).filter(Code.status == 'SUBSCRIBE').filter(
            Code.release_date <= one_week_later).all()
        session.close()
    for (index, code) in enumerate(codes):
        try:
            services.run_sub(code.code)
            logger.info(f"订阅番号{code.code}已执行完毕")
            if pt_wait():
                if index % 30 == 0:
                    time.sleep(600)
                else:
                    time.sleep(random.randint(60, 300))
        except Exception as e:
            logger.error(f"订阅番号{code.code}失败：{e}")


def pt_wait():
    settings = get_settings()
    if settings.MTEAM_API_KEY or settings.NICEPT_COOKIE or settings.PTT_COOKIE:
        return True
    return False


def run_actors():
    with session_scope() as session:
        actors = session.query(Actor).filter(isnot(Actor.limit_date, None)).all()
        for actor in actors:
            try:
                services.subscribe_code_by_actor(actor, session)
                logger.info(f"订阅演员{actor.name}影片,截止日期{actor.limit_date}已执行完毕")
            except Exception as e:
                logger.error(f"订阅演员{actor.name}失败：{e}")
                traceback.print_exc()
    download_un_exist_photo()


scheduler = BlockingScheduler()


def push_job():
    settings = get_settings()
    module = get_module()
    scheduler.add_job(sync_rank, trigger=CronTrigger(hour=4, minute=0))
    scheduler.add_job(run_news, trigger=CronTrigger(hour=5, minute=0))
    if module.qbittorrent.client:
        scheduler.add_job(module.qbittorrent.monitor_torrent, trigger=CronTrigger.from_crontab(expr="*/5 * * * *"))
    if module.transmission.client:
        scheduler.add_job(module.transmission.monitor_torrent, trigger=CronTrigger.from_crontab(expr="*/5 * * * *"))
    try:
        if settings.RANK_SCHEDULE_TIME:
            scheduler.add_job(sub_rank, trigger=CronTrigger.from_crontab(expr=settings.RANK_SCHEDULE_TIME))

        if settings.ACTOR_SCHEDULE_TIME:
            scheduler.add_job(run_actors, trigger=CronTrigger.from_crontab(expr=settings.ACTOR_SCHEDULE_TIME))

        if settings.DOWNLOAD_SCHEDULE_TIME:
            scheduler.add_job(run_codes, trigger=CronTrigger.from_crontab(expr=settings.DOWNLOAD_SCHEDULE_TIME))
    except Exception as e:
        logger.error(
            "cron表达式错误！至1.10.0版本开始定时程序仅支持5位cron表达式,请前往WEBUI修改,或者修改app.env文件并重启容器")


def start_scheduler():
    push_job()
    scheduler.start()


def restart_scheduler():
    scheduler.remove_all_jobs()
    push_job()


scheduler_thread = threading.Thread(target=lambda: start_scheduler())
