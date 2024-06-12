import os
import time
from datetime import datetime, timedelta
import threading
from glob import glob

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .. import GenPAC, Generator
from ..util import logger


# ====
def build(app):
    start_ts = time.time()
    with app.app_context():
        logger.info('GenPAC rebuild...')
        options = app.config.options
        try:
            Generator.clear_cache()
            gp = GenPAC(config_file=options.config_file)
            gp.add_job({'format': 'genpac-server-domains',
                        'output': options._private.domain_file,
                        '_order': -100})
            gp.add_job({'format': 'list',
                        'output': options._private.list_file,
                        '_order': -100})
            if options.server_rule_enabled:
                with open(options.server_rule_file, 'r') as fp:
                    for line in fp.readlines():
                        gp.add_rule(line.strip())
            gp.run(cli=False)
        except Exception:
            logger.error('GenPAC build fail.', exc_info=True)
        else:
            # 删除hash文件
            for hashfile in glob(os.path.join(options.target_path,
                                              '*.hash')):
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
        if event.is_directory:
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
        logger.debug(f'Watch Path: {path}')
        observer.schedule(event_handler, path, recursive=True)
    observer.start()


# 使用进程 uwsgi需使用参数--enable-threads
# REF:
# https://stackoverflow.com/questions/32059634/python3-threading-with-uwsgi
def start_watch(app):
    def _func():
        t = threading.Thread(target=watch_process, args=[app])
        t.setDaemon(True)
        t.start()
        return t
    return _func() if not app.debug else app.before_first_request_funcs.append(_func)
