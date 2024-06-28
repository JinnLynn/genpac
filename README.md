# GenPAC

[![pypi-version]][pypi] ![pypi-pyversions] [![pypi-license]][pypi] [![dev-version]](https://github.com/JinnLynn/genpac/tree/dev) [![build](https://github.com/JinnLynn/genpac/actions/workflows/build.yml/badge.svg)](https://github.com/JinnLynn/genpac/actions/workflows/build.yml) [![cook](https://github.com/JinnLynn/genpac/actions/workflows/cook.yml/badge.svg)](https://github.com/JinnLynn/genpac/actions/workflows/cook.yml)

基于[gfwlist][]的多种代理软件配置文件生成工具，支持自定义规则

目前支持的格式有: **PAC, Dnsmasq, V2Ray, Shadowsocks, Quantumult X, Shadowrocket, Surge, Wingy, Potatso** 和 **IP** (国别IP列表), **List** (gfwlist格式的列表), **Copy** (复制源)。[示例](https://github.com/JinnLynn/genpac/tree/cooked)

**注意**: 生成后的规则不会匹配网址路径，只会检查域名(包括子域名)，如`|http://sub2.sub1.domain.com/path/to/file.ext` => `sub2.sub1.domain.com`

## 安装

```shell
# 安装或更新
pip install genpac
# 安装开发版本
pip install https://github.com/JinnLynn/genpac/archive/dev.tar.gz

# 安装服务器组件
pip install genpac[server]
pip install "genpac[server] @ https://github.com/JinnLynn/genpac/archive/dev.tar.gz"

# 卸载
pip uninstall genpac
```

## 使用方法

### 命令行形式

```shell
genpac [--version] [--help] [--init [PATH]] [--format FMT] [--output FILE] [--config FILE] [--proxy PROXY] [--gfwlist-url URL]
              [--gfwlist-local FILE] [--gfwlist-update-local] [--gfwlist-disabled] [--gfwlist-decoded-save FILE] [--user-rule RULE]
              [--user-rule-from FILE] [--template FILE] [--etag-cache] [--pac-proxy PROXY] [--pac-precise] [--pac-compress]
              [--dnsmasq-dns DNS] [--dnsmasq-ipset IPSET] [--dnsmasq-nftset NFTSET] [--v2ray-proxy TAG] [--v2ray-direct TAG]
              [--v2ray-default TAG] [--v2ray-format {json,yaml}] [--ip-cc CC] [--ip-family {4,6,all}] [--ssacl-geocn] [--list-raw]
              [--qtx-no-direct] [--qtx-no-final] [--copy-source SRC] [--shadowrocket-policy POLICY] [--shadowrocket-no-direct]
              [--shadowrocket-no-final] [--shadowrocket-set] [--surge-policy POLICY] [--surge-no-direct] [--surge-no-final] [--surge-set]
              [--wingy-adapter-opts OPTS] [--wingy-rule-adapter-id ID]

获取gfwlist生成多种格式的翻墙工具配置文件, 支持自定义规则

options:
  --version, -v         版本信息
  --help, -h            帮助信息
  --init [PATH]         初始化配置和用户规则文件

通用参数:
  --format FMT, -f FMT  生成格式, 只有指定了格式, 相应格式的参数才可用
                        可选: pac,dnsmasq,v2ray,ip,ssacl,list,qtx,copy,shadowrocket,surge,wingy,potatso
  --output FILE, -o FILE
                        输出到文件, 无此参数或FILE为-, 则输出到stdout
  --config FILE, -c FILE
                        从文件中读取配置信息
  --proxy PROXY         在线获取外部数据时的代理, 如果可正常访问外部地址, 则无必要使用该选项
                        格式: [PROTOCOL://][USERNAME:PASSWORD@]HOST:PORT
                        其中协议、用户名、密码可选, 支持协议: http socks5 socks4 socks 如:
                          http://127.0.0.1:8080
                          SOCKS5://127.0.0.1:1080
                          SOCKS5://username:password@127.0.0.1:1080
  --gfwlist-url URL     gfwlist网址，无此参数或URL为空则使用默认地址, URL为-则不在线获取
  --gfwlist-local FILE  本地gfwlist文件地址, 当在线地址获取失败时使用
  --gfwlist-update-local
                        当在线gfwlist成功获取且--gfwlist-local参数存在时, 更新gfwlist-local内容
  --gfwlist-disabled    禁用gfwlist
  --gfwlist-decoded-save FILE
                        保存解码后的gfwlist, 仅用于测试
  --user-rule RULE      自定义规则, 允许重复使用或在单个参数中使用`,`分割多个规则，如:
                          --user-rule="@@sina.com" --user-rule="||youtube.com"
                          --user-rule="@@sina.com,||youtube.com"
  --user-rule-from FILE
                        从文件中读取自定义规则, 使用方法如--user-rule
  --template FILE       自定义模板文件
  --etag-cache          获取外部文件时是否使用If-None-Match头进行缓存检查

PAC:
  通过代理自动配置文件(PAC)系统或浏览器可自动选择合适的代理服务器

  --pac-proxy PROXY     代理地址, 如 SOCKS5 127.0.0.1:8080; SOCKS 127.0.0.1:8080
  --pac-precise         精确匹配模式
  --pac-compress        压缩输出

DNSMASQ:
  Dnsmasq配合iptables/ipset、nftables/nftset可实现基于域名的透明代理

  --dnsmasq-dns DNS     生成规则域名查询使用的DNS服务器，格式: HOST#PORT
                        默认: 127.0.0.1#53
  --dnsmasq-ipset IPSET
                        使用ipset, 允许重复或使用`,`分割多个,
                        如: GFWLIST,GFWLIST6
  --dnsmasq-nftset NFTSET
                        使用ntfset, 允许重复或使用`,`分割多个,
                        如: 4#inet#TABLE#GFWLIST,6#inet#TABLE#GFWLIST6

V2RAY:
  V2Ray的路由规则

  --v2ray-proxy TAG     代理标签，默认: proxy
  --v2ray-direct TAG    直连标签，未指定则不输出直连规则
  --v2ray-default TAG   默认标签，未指定则不输出默认规则
  --v2ray-format {json,yaml}
                        输出格式，默认: json

IP:
  国别IP地址列表

  --ip-cc CC            国家代码(ISO 3166-1) 默认: CN
  --ip-family {4,6,all}
                        IP类型 可选: 4, 6, all 默认: 4

SSACL:
  Shadowsocks访问控制列表

  --ssacl-geocn         国内IP不走代理，所有国外IP走代理

LIST:
  与GFWList格式相同的地址列表

  --list-raw            明文，不进行base64编码

QTX:
  Quantumult X 的分流规则

  --qtx-no-direct       不包含直连规则
  --qtx-no-final        不包含FINAL规则

COPY:
  IP地址列表

  --copy-source SRC     来源, 网址或文件路径

SHADOWROCKET:
  Shadowrocket(小火箭)代理规则

  --shadowrocket-policy POLICY
                        代理规则策略: 默认: PROXY
  --shadowrocket-no-direct
                        不包含直连规则
  --shadowrocket-no-final
                        不包含FINAL规则
  --shadowrocket-set    输出为规则集

SURGE:
  Surge代理规则

  --surge-policy POLICY
                        代理规则策略: 默认: PROXY
  --surge-no-direct     不包含直连规则
  --surge-no-final      不包含FINAL规则
  --surge-set           输出为规则集

WINGY:
  Wingy是iOS下基于NEKit的代理App, 无可用参数
  * 注意: 即将废弃 *

  --wingy-adapter-opts OPTS
                        adapter选项, 选项间使用`,`分割, 多个adapter使用`;`分割, 如:
                          id:ap1,type:http,host:127.0.0.1,port:8080;id:ap2,type:socks5,host:127.0.0.1,port:3128
  --wingy-rule-adapter-id ID
                        生成规则使用的adapter ID

POTATSO:
  Potatso2是iOS下基于NEKit的代理App, 无可用参数
  * 注意: 即将废弃 *
```

### web服务形式

支持以web形式自动生成及输出:

```shell
# 安装服务组件
pip install genpac[server]
pip install "genpac[server] @ https://github.com/JinnLynn/genpac/archive/dev.tar.gz"

# 本地运行
genpac.server --config="/PATH/TO/CONFIG/FILE"

# Docker 运行
# 测试
docker run --rm -p 8000:8000 jinnlynn/genpac
# 自定义配置文件
docker run --rm -p 8000:8000 -v /PATH/TO/CONFIG/FILE:/app/etc/config.ini jinnlynn/genpac
```

配置参考见[example/server/config.ini][]

## 配置文件

支持通过 `--config` 参数读入配置信息，配置文件书写方法可参考[example/config.ini][]

## 自定义规则

支持通过 `--user-rule` 自定义单个规则或 `--user-rule-from` 读入自定义规则文件，这两个参数均可重复使用。

自定义规则文件可参考[example/user-rules.txt][]

自定义规则的语法与gfwlist相同，使用AdBlock Plus过滤规则( http://adblockplus.org/en/filters )，简述如下:

1. 通配符支持，如 `*.example.com/*` 实际书写时可省略 `*` 为 `.example.com/`
2. 正则表达式支持，以 `\` 开始和结束，如 `\[\w]+:\/\/example.com\\`
3. 例外规则 `@@` ，如 `@@*.example.com/*` 满足 `@@` 后规则的地址不使用代理
4. 匹配地址开始和结尾 `|` ，如 `|http://example.com` 、 `example.com|` 分别表示以 `http://example.com` 开始和以 `example.com` 结束的地址
5. `||` 标记，如 `||example.com` 则 `http://example.com https://example.com ftp://example.com` 等地址均满足条件
6. 注释 `!` 如 `! Comment`

配置自定义规则时需谨慎，尽量避免与gfwlist产生冲突，或将一些本不需要代理的网址添加到代理列表

规则优先级从高到底为: user-rule > user-rule-from > gfwlist

## FAQ

1. 出现`fetch gfwlist fail.`错误

   gfwlist是在线获取，某些情况下可能被和谐或其它原因导致获取失败，可以通过以下几种方法解决该问题：
   * 使用`--proxy`参数，通过代理获取gfwlist
   * 通过其它方式下载到本地，再通过`--gfwlist-local`加载
   * 使用参数`--gfwlist-url=-`不进行在线获取，这种情况下你只能使用自定义规则

1. gfwlist获取代理使用失败

   * 检查--proxy参数或配置proxy值是格式否符合`PROTOCOL://HOST:POST`，如`socks5://127.0.0.1:1080、http://127.0.0.1:8080`
   * OSX Linux如果存在http_proxy、https_proxy环境变量，代理可能无法正常使用

1. PAC格式中，参数`--pac-precise`的精确匹配模式的作用是什么？

   1.4.0之后生成的PAC文件默认只对域名进行匹配，如规则`.ftchinese.com/channel/video`处理后为`ftchinese.com`，所有在`ftchinese.com`下的网址都将通过匹配，在这种模式下可以减少PAC文件尺寸，并在一定程度上提高效率，推荐使用，但如果你依然想用原有的规则进行精确的网址匹配判断，则使用参数`--pac-precise`或在配置文件中设置`pac-precise=true`即可。

1. genpac命令未找到

   可能是因为`genpac`命令没有被安装到系统路径，如Ububtu 16.04且通过apt-get安装的pip的环境下，`genpac`执行入口文件被安装到了`~/.local/bin`，遇到这种情况，将`~/.local/bin`添加到系统路径，或卸载重新使用sudo安装，都可以解决问题。

### 示例

```shell
# 从gfwlist生成代理信息为SOCKS5 127.0.0.1:1080的PAC文件
genpac --format=pac --pac-proxy="SOCKS5 127.0.0.1:1080; DIRECT"

# 从~/config.ini读取配置生成
genpac --config=~/config.ini

# PAC格式 压缩
genpac --format=pac --pac-proxy="SOCKS5 127.0.0.1:1080" --pac-compress

# PAC格式 精确匹配模式
genpac --format=pac --pac-proxy="SOCKS5 127.0.0.1:1080" --pac-precise

# PAC格式 自定义规则
genpac --format=pac --pac-proxy="SOCKS5 127.0.0.1:1080" --user-rule="||example.com" --user-rule-from=~/user-rule.txt

# PAC格式 多个自定义规则文件
genpac --format=pac --pac-proxy="SOCKS5 127.0.0.1:1080" --user-rule="||example.com" --user-rule="||example2.com" --user-rule-from=~/user-rule.txt,~/user-rule2.txt

# PAC格式 使用HTTP代理127.0.0.1:8080获取在线gfwlist文件
genpac --format=pac --pac-proxy="SOCKS5 127.0.0.1:1080" --proxy="http://127.0.0.1:8080"

# PAC格式 如果在线gfwlist获取失败使用本地文件，如果在线gfwlist获取成功更新本地gfwlist文件
genpac --format=pac --pac-proxy="SOCKS5 127.0.0.1:1080" --gfwlist-local=~/gfwlist.txt --update-gfwlist-local

# PAC格式 忽略gfwlist，仅使用自定义规则
genpac --format=pac --pac-proxy="SOCKS5 127.0.0.1:1080" --gfwlist-disabled --user-rule-from=~/user-rule.txt
genpac --format=pac --pac-proxy="SOCKS5 127.0.0.1:1080" --gfwlist-url=- --user-rule-from=~/user-rule.txt

# 其它输出格式同样可以使用上述PAC格式中关于gfwlist和自定义规则的参数

# DNSMASQ
genpac --format=dnsmasq --dnsmasq-dns="127.0.0.1#5353" --dnsmasq-ipset="SET_NAME"
genpac --format=dnsmasq --dnsmasq-dns="127.0.0.1#5353" --dnsmasq-nftset="4#inet#TABLE#GFWLIST,6#inet#TABLE#GFWLIST6"
genpac --format=dnsmasq --dnsmasq-nftset="4#inet#TABLE#GFWLIST,6#inet#TABLE#GFWLIST6"

# V2RAY
genpac --format=v2ray --v2ray-proxy-tag="proxy"
genpac --format=v2ray --v2ray-proxy-tag="proxy" --v2ray-direct-tag="direct"
genpac --format=v2ray --v2ray-proxy-tag="proxy" --v2ray-format="yaml"

# IP
genpac --format=ip --ip-cc="cn" --ip-family="all"
genpac --format=ip --ip-cc="us" --ip-family="6"

# Shadowrocket
genpac --format=shadowrocket --shadowrocket-policy="PROXY"

# Surge
genpac --format=surge --surge-policy="PROXY"

# ...
```

[gfwlist]:                  https://github.com/gfwlist/gfwlist
[example/config.ini]:        https://github.com/JinnLynn/genpac/blob/master/example/config.ini
[example/user-rules.txt]:    https://github.com/JinnLynn/genpac/blob/master/example/user-rules.txt
[example/server/config.ini]: https://github.com/JinnLynn/genpac/blob/master/example/server/config.ini
[pypi]:             https://pypi.python.org/pypi/genpac
[pypi-version]:     https://img.shields.io/pypi/v/genpac
[pypi-license]:     https://img.shields.io/pypi/l/genpac
[pypi-pyversions]:  https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fgithub.com%2FJinnLynn%2Fgenpac%2Fraw%2Fmaster%2Fpyproject.toml

[dev-version]:      https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fgithub.com%2FJinnLynn%2Fgenpac%2Fraw%2Fdev%2Fpyproject.toml&query=%24.project.version&style=flat&label=dev&prefix=v
