# GenPAC

[![pypi-version]][pypi] [![pypi-license]][pypi] [![travis-ci-status]][travis-ci]

基于gfwlist的代理自动配置(Proxy Auto-config)文件生成工具，支持自定义规则。

Generate PAC file from gfwlist, custom rules supported. 

### Installation

```shell
# 安装
$ pip install genpac
# 或从github安装开发版本
$ pip install https://github.com/JinnLynn/genpac/archive/master.zip

# 更新
$ pip install --upgrade genpac
# 或从github更新开发版本
$ pip install --upgrade https://github.com/JinnLynn/genpac/archive/master.zip

# 卸载
$ pip uninstall genpac
```

**注意：** 如果安装后，执行时出现无法找到命令的错误，可能是因为`genpac`命令没有被安装到系统路径，如Ububtu 16.04且通过apt-get安装的pip的环境下，`genpac`执行入口文件被安装到了`~/.local/bin`，遇到这种情况，将`~/.local/bin`添加到系统路径，或卸载重新使用sudo安装，都可以解决问题。

### Usage

```
genpac [-h|--help] [-v|version]
       [-p PROXY|--proxy=PROXY]
       [--gfwlist-url=URL] [--gfwlist-proxy=PROXY]
       [--gfwlist-local=FILE] [--update-gfwlist-local]
       [--gfwlist-disabled]
       [--user-rule=RULE] [--user-rule-from=FILE]
       [-c FILE|--config-from=FILE] [-o FILE|--output=FILE]
       [-z|--compress]
       [-P|--precise]
       [--init[=PATH]]

可选参数:
  -h, --help                帮助
  -v, --version             版本信息
  -p PROXY, --proxy=PROXY   PAC文件中使用的代理信息, 如:
                              SOCKS 127.0.0.1:8080
                              SOCKS5 127.0.0.1:8080; SOCKS 127.0.0.1:8080
                              PROXY 127.0.0.1:8080
  --gfwlist-proxy=PROXY     获取gfwlist时的代理设置, 如果你可以正常访问gfwlist, 则无必要使用该选项
                            格式为 "代理类型 [用户名:密码]@地址:端口" 其中用户名和密码可选, 如:
                              SOCKS5 127.0.0.1:8080
                              SOCKS5 username:password@127.0.0.1:8080
  --gfwlist-url=URL         gfwlist网址，无此参数或URL为空则使用默认地址, URL为-则不在线获取
                              https://raw.githubusercontent.com/gfwlist/gfwlist/master/gfwlist.txt
  --gfwlist-local=FILE      本地gfwlist文件地址, 当在线地址获取失败时使用
  --update-gfwlist-local    当在线gfwlist成功获取且gfwlist-local存在时, 更新gfwlist-local内容
  --gfwlist-disabled        禁用gfwlist
  --user-rule=RULE          自定义规则, 该参数允许重复使用或在单个参数中使用`,`分割多个规则，如:
                              --user-rule="@@sina.com" --user-rule="||youtube.com"
                              --user-rule="@@sina.com,||youtube.com"
  --user-rule-from=FILE     从文件中读取自定义规则, 该参数使用规则与--user-rule相同
  -c FILE, --config-from=FILE
                            从文件中读取配置信息
  -o FILE, --output=FILE    输出到文件, 无此参数或FILE为-, 意味着输出到stdout
  -z, --compress            压缩输出
  -P, --precise             精确匹配模式
  --init[=PATH]             初始化配置和用户规则文件
```

### Config

支持通过 `--config-from` 参数读入配置信息，配置文件书写方法可参考[config-sample.ini][]

### Custom Rules

支持通过 `--user-rule` 自定义单个规则或 `--user-rule-from` 读入自定义规则文件，这两个参数均可重复使用。

自定义规则文件可参考[user-rules-sample.txt][]

自定义规则的语法与gfwlist相同，使用AdBlock Plus过滤规则( http://adblockplus.org/en/filters )，简述如下:
  
1. 通配符支持，如 `*.example.com/*` 实际书写时可省略 `*` 为 `.example.com/`
2. 正则表达式支持，以 `\` 开始和结束，如 `\[\w]+:\/\/example.com\\`
3. 例外规则 `@@` ，如 `@@*.example.com/*` 满足 `@@` 后规则的地址不使用代理
4. 匹配地址开始和结尾 `|` ，如 `|http://example.com` 、 `example.com|` 分别表示以 `http://example.com` 开始和以 `example.com` 结束的地址
5. `||` 标记，如 `||example.com` 则 `http://example.com https://example.com ftp://example.com` 等地址均满足条件
6. 注释 `!` 如 `! Comment`

配置自定义规则时需谨慎，尽量避免与gfwlist产生冲突，或将一些本不需要代理的网址添加到代理列表

规则优先级从高到底为: user-rule > user-rule-from > gfwlist

### FAQ

1. 参数`--precise`的精确匹配模式的作用是什么？

   1.4.0之后生成的PAC文件默认只对域名进行匹配，如规则`.ftchinese.com/channel/video`处理后为`ftchinese.com`，所有在`ftchinese.com`下的网址都将通过匹配，在这种模式下可以减少PAC文件尺寸，并在一定程度上提高效率，推荐使用，但如果你依然想用原有的规则进行精确的网址匹配判断，则使用参数`--precise`或在配置文件中设置`precise=true`即可。

1. 出现`fetch gfwlist fail. `错误
  
   gfwlist是在线获取，某些情况下可能被和谐或其它原因导致获取失败，可以通过以下几种方法解决该问题：
   * 使用`--gfwlist-proxy`参数，通过代理获取gfwlist
   * 通过其它方式下载到本地，再通过`--gfwlist-local`加载
   * 使用参数`--gfwlist-url=-`不进行在线获取，这种情况下你只能使用自定义规则

1. gfwlist获取代理使用失败

   * 检查--gfwlist-proxy参数或配置gfwlist-proxy值是格式否符合`TYPE HOST:POST`，如`SOCKS5 127.0.0.1:1080、PROXY 127.0.0.1:8080`
   * OSX Linux如果存在http_proxy、https_proxy环境变量，代理可能无法正常使用

1. genpan命令未找到
   
   见前文安装章节的注意事项。

### Examples

```
# 从gfwlist生成代理信息为SOCKS5 127.0.0.1:1080
genpac -p "SOCKS5 127.0.0.1:1080"

# 从~/config.ini读取配置生成
genpac --config-from=~/config.ini

# 压缩
genpac -p "SOCKS5 127.0.0.1:1080" -z

# 精确匹配模式
genpac -p "SOCKS5 127.0.0.1:1080" -P

# 自定义规则
genpac -p "SOCKS5 127.0.0.1:1080" --user-rule="||example.com" --user-rule-from=~/user-rule.txt
genpac --config-from=~/config.ini -p "SOCKS5 127.0.0.1:1080" --user-rule="||example.com" --user-rule-from=~/user-rule.txt

# 多个自定义规则文件
genpac -p "SOCKS5 127.0.0.1:1080" --user-rule="||example.com" --user-rule="||example2.com" --user-rule-from=~/user-rule.txt,~/user-rule2.txt

# 使用HTTP代理127.0.0.1:8080获取在线gfwlist文件
genpac -p "SOCKS5 127.0.0.1:1080" --gfwlist-proxy="PROXY 127.0.0.1:8080"

# 如果在线gfwlist获取失败使用本地文件，如果在线gfwlist获取成功更新本地gfwlist文件
genpac -p "SOCKS5 127.0.0.1:1080" --gfwlist-local=~/gfwlist.txt --update-gfwlist-local

# 忽略gfwlist，仅使用自定义规则
genpac -p "SOCKS5 127.0.0.1:1080" --gfwlist-disabled --user-rule-from=~/user-rule.txt
genpac -p "SOCKS5 127.0.0.1:1080" --gfwlist-url=- --user-rule-from=~/user-rule.txt
```

[gfwlist]: https://raw.githubusercontent.com/gfwlist/gfwlist/master/gfwlist.txt
[config-sample.ini]: https://github.com/JinnLynn/genpac/blob/master/genpac/res/config-sample.ini
[user-rules-sample.txt]: https://github.com/JinnLynn/genpac/blob/master/genpac/res/user-rules-sample.txt
[pypi]:             https://pypi.python.org/pypi/genpac
[travis-ci]:        https://travis-ci.org/JinnLynn/genpac
[pypi-version]:     https://img.shields.io/pypi/v/genpac.svg?style=flat&maxAge=86400
[pypi-license]:     https://img.shields.io/pypi/l/genpac.svg?style=flat&maxAge=86400
[travis-ci-status]: https://img.shields.io/travis/JinnLynn/genpac.svg?style=flat&maxAge=86400
[dev-badge]:        https://img.shields.io/badge/dev-1.4.1b1-orange.svg?style=flat&maxAge=86400