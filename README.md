# PAC Generator

代理自动配置(Proxy Auto-config)文件生成工具。

* 判断条件基于gfwlist
* 获取gfwlist时允许独立设置代理

## USAGE

### 配置

用任意文本编辑工具打开genpac.py文件，根据文件内的注释配置相应的变量。

### 生成

开发语言为Python，版本要求2.7。

Mac OSX已自带Python，在终端执行`./genpac.py`即可。

Windows需要安装Python，在其[官网][3]可以找到安装包（**版本务必选择2.7**），安装后在命令行执行`python genpac.py`即可

*nix与Mac OSX类似。

### 使用

如何使用自动代理请自行Google，需要说明的是Mac OSX Lion下的Safari由于其沙盒机制的原因无法使用本地PAC文件，需要使用Web Sharing或将PAC文件放在服务器，然后通过http访问。

## Copyright and license

Copyright 2012 [Jeeker.net][1], Licensed under [CC BY 3.0][2].

[1]:http://jeeker.net
[2]:http://creativecommons.org/licenses/by/3.0/
[3]:http://www.python.org/