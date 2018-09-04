# worker 

## 目录  
* [项目介绍](#项目介绍)  
* [使用说明](#使用说明)  
  * [获取代码](#获取代码)  
  * [使用实例](#使用实例)  
* [其他](#其他)  
  
<a name="项目介绍"></a>  
## 项目介绍  
*worker* 是一个简单的任务运行框架， 它可以用来多并发的运行常驻任务以及定时任务。 <br>
*worker* 实现了安全的退出，你可以在任意时间内KILL掉主进程， 它会尽可能的等待所有任务完成后退出， 再也不用怕数据丢失。 <br>
*worker* 是一个无依赖的框架，不必安装其他任何第三方库，同时它支持python2以及python3。 <br>
*worker* 在运行5000个定时任务以及500个常驻任务时能够做到定时任务最大延时1秒（我相信如果任务量这么大，你也不会使用这么简单的任务框架）。<br>
*worker* 内部限制了进程以及线程的最大开启数量，因此你不必担心占用过多的系统资源。<br>
  
<a name="使用说明"></a>  
## 使用说明  
  
<a name="获取代码"></a>  
### 获取代码  
 
* github 项目主页: <https://github.com/QYLGitHub/worker>  
  
<a name="使用实例"></a>  
## 使用实例
#### 安装
```
克隆项目至本地
git clone https://github.com/QYLGitHub/worker.git
cd worker
python setup.py install
```
#### 代码中使用
```python
from worker.worker import Worker
w = Worker()
# 添加一个每过5秒运行一次的任务
w.add_run_interval(lambda : None, interval_time=5)
# 添加一个常驻任务，并同时运行10个此任务
w.add_run_forever(lambda : None, run_num=10)
# 添加一个当主进程结束时需要运行的任务
w.add_kill_callback(lambda : None)
# 启动框架
w.start()
```

#### 其他
由于本人编程水平有限<br>
如果各位朋友有更好的想法、更好的实现或是发现bug.欢迎提issue或者fork修改!<br>
最后祝各位生活愉快!<br> ![Shurnim icon](https://github.com/QYLGitHub/SpiderMan/raw/master/SpiderMan/server/web/templates/static/images/readme/end.jpg)
## Credits
This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [audreyr/cookiecutter-pypackage](https://github.com/audreyr/cookiecutter-pypackage) project template.
