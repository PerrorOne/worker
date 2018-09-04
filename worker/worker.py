# -*- coding: utf-8 -*-
import os
import time
import signal
import traceback
import logging
import platform
import threading
import multiprocessing
from multiprocessing import cpu_count
from concurrent.futures import ThreadPoolExecutor

WIN_SYSTEM = "WINDOWS"
_thread_lock = threading.Lock()
log = logging.getLogger("Worker")


def set_log(format, level):
    logging.basicConfig(format=format, level=level)


def split_list_n(ls, n):
    """接受一个list, 将list均分n份并返回"""
    if not isinstance(ls, list) or not isinstance(n, int):
        return []
    ls_len = len(ls)
    if n <= 0 or 0 == ls_len:
        return [ls]
    if n > ls_len:
        return [ls]
    elif n == ls_len:
        return [[i] for i in ls]
    else:
        j = ls_len // n
        ls_return = []
        for i in range(0, (n - 1) * j, j):
            ls_return.append(ls[i:i + j])
        ls_return.append(ls[(n - 1) * j:])
        return ls_return


class Worker(object):
    """任务运行类, 任务分为永久运行以及定时运行.

    Use:
        >>>p = Worker()
        # 添加一个永久运行任务, 设置10个任务同时运行
        >>>p.add_run_forever(lambda : None, run_num=10)
        # 添加一个定时任务, 每10秒运行一次
        >>>p.add_run_interval(lambda :None, interval_time=10)
        # 开始运行
        >>>p.start()
        # 捕获SystemExit异常,以便在主进程退出时能够做进一步的操作
        >>>try:
        ... p.start()
        ...except SystemExit:
        ... pass  # do something
        # 或者使用callback在主进程退出时运行的函数
        >>> p.add_kill_callback(lambda : print("do something...")).start()
    """
    def __init__(self, log_format=None, log_level=logging.INFO):
        self.jobs = []
        self.job_thread_process = []
        self.alive = True
        self.masert = os.getpid()
        self._now_system = platform.system().upper()
        if not log_format:
            log_format = "%(asctime)s - %(name)s - %(levelname)s : %(message)s"
        set_log(log_format, log_level)
        if WIN_SYSTEM in self._now_system:
            log.warning("The current system is: windows."
                        " child process cannot exit safely.")

    def is_masert(self):
        return self.masert == os.getpid()

    def _run_job(self, jobs):
        signal.signal(signal.SIGTERM, self.shutdown)
        run_count = sum([i["run_num"] for i in jobs])
        # 开启线程数量不得超过cpu_count * 5
        t = ThreadPoolExecutor(cpu_count() * 5 if run_count > cpu_count() * 5 else run_count)
        for job in jobs:
            if job.get("interval_time", 0) != 0:
                t.submit(self._run_interval_func, job)
            else:
                for i in range(job["run_num"]):
                    t.submit(self._run_forever_func, job)
        t.shutdown(True)

    def add_run_forever(self, fn, run_num=1):
        """添加一个永久运行函数,该函数中不应该包含任何死循环.

        :param fn: 定时任务函数.
        :param run_num: 并发的数量,默认为1.
        """
        if not callable(fn):
            raise TypeError("Parameter 'fn' must be callable. not {}".format(type(fn)))
        self.jobs.append({
            "func": fn,
            "run_num": run_num or 1,
        })
        return self

    def add_run_interval(self, fn, interval_time=0, run_num=1):
        """添加一个定时函数,该函数中不能包含任何死循环.

        :param fn: 定时任务函数
        :param interval_time: 运行间隔时间,单位秒
        :param run_num: 并发的数量,默认为1, TODO: 如果并发数量过大那么定不定时又有何用?
        """
        if not interval_time:
            return
        if not callable(fn):
            raise TypeError("Parameter 'fn' must be callable. not {}".format(type(fn)))
        self.jobs.append({
            "func": fn,
            "interval_time": interval_time,
            "run_num": run_num or 1,
        })
        return self

    @staticmethod
    def _get_time():
        return time.time()

    def _run_forever_func(self, job):
        while self.alive:
            log.debug("Run forever function")
            # noinspection PyBroadException
            try:
                job["func"]()
            except Exception as _:
                traceback.print_exc()
                self.shutdown(is_slave=True)
                return
            time.sleep(.0001)

    def _func(self, fn):
        # noinspection PyBroadException
        try:
            fn()
        except Exception as _:
            traceback.print_exc()
            self.shutdown(is_slave=True)

    def _run_interval_func(self, job):
        # 定时任务的特殊性, 必须开启新的子线程运行
        t = ThreadPoolExecutor(cpu_count() * 2)
        while self.alive:
            if not job.get("last_run_time", 0):
                job["last_run_time"] = self._get_time()

            if self._get_time() - job["last_run_time"] >= job["interval_time"]:
                t.submit(self._func, job["func"])
                with _thread_lock:
                    job["last_run_time"] = self._get_time()
            log.debug("Run interval function")
            time.sleep(.0001)
        t.shutdown(True)

    def add_kill_callback(self, fn):
        """添加主进程被kill时运行的函数,该函数不应该包含死循环否则无法结束程序"""
        self.kill_callback_func = fn
        log.debug("add kill callback function: {}".format(fn.__name__))

    def start(self):
        self._run_works()

    def _run_works(self):
        if not self.jobs:
            log.error("No task was added. you can: p.add_run_interval(func, interval_time=5)")
            return
        log.info("{} starting...".format(self.__class__.__name__))
        signal.signal(signal.SIGINT, self.shutdown)
        data = []
        for _jobs in split_list_n(self.jobs, cpu_count()):
            t = multiprocessing.Process(target=self._run_job, args=(_jobs,))
            t.start()
            data.append(t)
        log.info("Add total number of tasks: {} ".format(len(self.jobs)))
        log.info("started with {} processes({})".format(len(data), self.masert))
        self.job_thread_process = data
        while self.alive:
            time.sleep(1)

    def shutdown(self, *args, **kwargs):
        if not self.is_masert():
            self.alive = False
            if kwargs.get("is_slave", None):
                os.kill(self.masert, signal.SIGINT)
            return

        log.info("Shutting down {}".format(self.__class__.__name__))
        while len(self.job_thread_process):
            for i in list(self.job_thread_process):
                if not i.is_alive():
                    self.job_thread_process.remove(i)
                    continue
                # TODO: 在win系统中使用os.kill会出现权限问题,使用taskkill则子进程不能安全退出
                if WIN_SYSTEM in self._now_system:
                    os.system("taskkill /F /pid {}".format(i.pid))
                else:
                    os.kill(i.pid, signal.SIGTERM)
            time.sleep(.0001)

        if getattr(self, "kill_callback_func", None):
            log.debug("runing kill_callback_func: "
                      "{}".format(self.kill_callback_func.__name__))
            self.kill_callback_func()
        self.alive = False
        log.info("{} exit...".format(self.__class__.__name__))
        exit(0)
