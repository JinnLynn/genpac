import os
import shutil
import time
from datetime import datetime, timedelta
import threading
from glob import glob

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, \
    EVENT_TYPE_CLOSED, EVENT_TYPE_OPENED

from .. import GenPAC, Generator
from ..util import logger


# ====
def build(app):
    start_ts = time.time()
    with app.app_context():
        logger.info('GenPAC rebuild...')
        options = app.config.options

        for f in glob(os.path.join(options.target, '*')):
            if f in options._private.protected_files:
                continue
            try:
                logger.debug(f'delete: {f}')
                shutil.rmtree(f) if os.path.isdir(f) else os.remove(f)
            except Exception as e:
                logger.warning(f'delete fail: {f} {e}')

        try:
            Generator.clear_cache()
            gp = GenPAC(config_file=options.config_file)
            gp.add_job({'format': 'genpac-server-domains',
                        'output': options._private.domain_file,
                        '_order': -1})
            gp.add_job({'format': 'list',
                        'output': options._private.list_file,
                        '_order': -1})
            if options.server_rule_enabled:
                with open(options._private.server_rule_file, 'r') as fp:
                    gp.add_rule(fp.readlines())
            gp.parse_options(cli=False, workdir=options.target)
            gp.generate_all()
        except Exception:
            logger.error('GenPAC build fail.', exc_info=True)
        else:
            # 删除hash文件
            for hashfile in glob(os.path.join(options.target, '*.hash')):
                os.remove(hashfile)
            logger.info('GenPAC build success. [%.3fs]', time.time() - start_ts)
            app.extensions['genpac'].domains_outdate = True
            app.extensions['genpac'].last_builded = time.time()


def autobuild_task(app, event='CRON'):
    logger.info(f'Autobuild[{event}]...')
    build(app)


class WatchHandler(FileSystemEventHandler):
    def __init__(self, app):
        super().__init__()
        self.app = app

    def on_any_event(self, event):
        if event.is_directory or event.event_type in [EVENT_TYPE_OPENED, EVENT_TYPE_CLOSED]:
            return None

        logger.debug(f'File Event[{event.event_type}]: {event.src_path}')
        # 添加到一次任务延时执行，防止多次响应
        self.app.apscheduler.add_job('build_file_change', autobuild_task,
                                     trigger='date', run_date=datetime.now() + timedelta(seconds=3),
                                     args=(self.app,), kwargs={'event': 'WATCH'},
                                     replace_existing=True)


def watch_process(app):
    observer = Observer()
    event_handler = WatchHandler(app)
    for path in app.config.options.watch_files:
        logger.debug(f'Watch: {path}')
        observer.schedule(event_handler, path, recursive=True)
    observer.start()


# 使用进程 uwsgi需使用参数--enable-threads
# REF:
# https://stackoverflow.com/questions/32059634/python3-threading-with-uwsgi
def start_watch(app):
    thread = threading.Thread(target=watch_process, args=[app], daemon=True)
    thread.start()
    return thread
