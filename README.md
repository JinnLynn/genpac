# GenPAC

[![pypi-version]][pypi] [![pypi-license]][pypi]

基于gfwlist的代理自动配置(Proxy Auto-config)文件生成工具，支持自定义规则。

Generate PAC file from gfwlist, custom rules supported. 

### INSTALL

```shell
$ pip install genpac
```

### COMMAND

```
genpac [-h|--help] [-v|version]
       [-p PROXY|--proxy=PROXY]
       [--gfwlist-url=URL] [--gfwlist-proxy=PROXY]
       [--gfwlist-local=FILE] [--disable-overwrite]
       [--user-rule=RULE] [--user-rule-from=FILE]
       [--config-from=FILE] [--output=FILE]
       [-c|--compress]

可选参数:
  -h, --help                显示帮助内容
  -v, --version             显示版本信息
  -p PROXY, --proxy=PROXY   PAC文件中使用的代理信息，如:
                              SOCKS 127.0.0.1:8080
                              SOCKS5 127.0.0.1:8080; SOCKS 127.0.0.1:8080
                              PROXY 127.0.0.1:8080
  --gfwlist-url=URL         gfwlist地址，一般不需要更改，默认: 
                              https://autoproxy-gfwlist.googlecode.com/svn/trunk/gfwlist.txt
  --gfwlist-proxy=PROXY     获取gfwlist时的代理设置，如果你可以正常访问gfwlist，则无必要使用该选项
                            格式为 "代理类型 [用户名:密码]@地址:端口" 其中用户名和密码可选，如: 
                              SOCKS5 127.0.0.1:8080
                              SOCKS5 username:password@127.0.0.1:8080
  --gfwlist-local=FILE      本地gfwlist文件地址，当在线地址获取失败时使用
  --disable-overwrite
                            当在线gfwlist成功获取且--gfwlist-local存在时，默认会将在线内容覆盖到本地
                            此项设置后则不覆盖
  --user-rule=RULE          自定义规则，该选项允许重复使用，如:
                              --user-rule="@@sina.com"
                              --user-rule="||youtube.com"
  --user-rule-from=FILE     从文件中读取自定义规则，该选项允许重复使用
  --config-from=FILE        从文件中读取配置信息
  --output=FILE             输出生成的文件，如果没有此选项，将直接打印结果
  -c, --compress            压缩输出
```

### CONFIG

支持通过`--config-from`参数读入配置信息，配置文件书写方法可参考[sample/config.ini][]

### CUSTOM RULES

支持通过`--user-rule`自定义单个规则或`--user-rule-from`读入自定义规则文件，这两个参数均可重复使用。

自定义规则文件可参考[sample/user-rules.txt][]

自定义规则的语法与gfwlist相同，使用AdBlock Plus过滤规则( http://adblockplus.org/en/filters )，简述如下:
  
1. 通配符支持，如`*.example.com/*` 实际书写时可省略`*`为`.example.com/`
2. 正则表达式支持，以`\`开始和结束， 如`\[\w]+:\/\/example.com\\`
3. 例外规则 `@@`，如`@@*.example.com/*` 满足`@@`后规则的地址不使用代理
4. 匹配地址开始和结尾 |，如`|http://example.com`、`example.com|`分别表示以`http://example.com`开始和以`example.com`结束的地址
5. `||` 标记，如`||example.com` 则`http://example.com https://example.com ftp://example.com`等地址均满足条件
6. 注释 `!` 如`! Comment`

配置自定义规则时需谨慎，尽量避免与gfwlist产生冲突，或将一些本不需要代理的网址添加到代理列表

规则优先级从高到底为: user-rule > user-rule-from > gfwlist


[gfwlist]: http://autoproxy-gfwlist.googlecode.com/svn/trunk/gfwlist.txt
[sample/config.ini]: https://github.com/JinnLynn/genpac/blob/master/sample/config.ini
[sample/user-rules.txt]: https://github.com/JinnLynn/genpac/blob/master/sample/user-rules.txt
[pypi]:             https://pypi.python.org/pypi/genpac
[pypi-version]:     https://img.shields.io/pypi/v/genpac.svg?style=flat
[pypi-license]:     https://img.shields.io/pypi/l/genpac.svg?style=flat