# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys, os
reload(sys)
sys.setdefaultencoding('utf-8')
del sys.setdefaultencoding

import socks, socket, urllib2
import argparse
from pprint import pprint
import re
import base64
import time
from ConfigParser import ConfigParser
import logging

__version__ = '1.0.1'
__author__ = 'JinnLynn'
__author_email__ = 'eatfishlin@gmail.com'
__project_page__ = 'http://jeeker.net/projects/genpac/'

_help = '''
基于gfwlist的代理自动配置(Proxy Auto-config)文件生成工具

genpac [-h|--help] [-v|version] [--verbose]
       [-p PROXY|--proxy=PROXY]
       [--gfwlist-url=URL] [--gfwlist-proxy=PROXY]
       [--user-rule=RULE] [--user-rule-from=FILE]
       [--config-from=FILE] [--output=FILE]

可选参数:
  -h, --help                显示帮助内容
  -v, --version             显示版本信息
  --verbose                 输出详细处理过程
  -p PROXY, --proxy=PROXY   PAC文件中使用的代理信息，如:
                              SOCKS 127.0.0.1:9527
                              SOCKS5 127.0.0.1:9527; SOCKS 127.0.0.1:9527
                              PROXY 127.0.0.1:9527
  --gfwlist-url=URL         gfwlist地址，一般不需要更改，默认: 
                              http://autoproxy-gfwlist.googlecode.com/svn/trunk/gfwlist.txt
  --gfwlist-proxy=PROXY     获取gfwlist时的代理设置，如果你可以正常访问gfwlist，则无必要使用该选项
                            格式为 "代理类型 [用户名:密码]@地址:端口" 其中用户名和密码可选，如: 
                              SOCKS5 127.0.0.1:9527
                              SOCKS5 username:password@127.0.0.1:9527
  --user-rule=RULE          自定义规则，该选项允许重复使用，如:
                              --user-rule="@@sina.com"
                              --user-rule="||youtube.com"
  --user-rule-from=FILE     从文件中读取自定义规则，该选项允许重复使用
  --config-from=FILE        从文件中读取配置信息
  --output=FILE             输出生成的文件，如果没有此选项，将直接打印结果


用户自定义规则语法:
 
  与gfwlist相同，使用AdBlock Plus过滤规则( http://adblockplus.org/en/filters )
  
    1. 通配符支持，如 *.example.com/* 实际书写时可省略*为 .example.com/
    2. 正则表达式支持，以\开始和结束， 如 \[\w]+:\/\/example.com\\
    3. 例外规则 @@，如 @@*.example.com/* 满足@@后规则的地址不使用代理
    4. 匹配地址开始和结尾 |，如 |http://example.com、example.com|分别表示以http://example.com开始和以example.com结束的地址
    5. || 标记，如 ||example.com 则http://example.com、https://example.com、ftp://example.com等地址均满足条件
    6. 注释 ! 如 ! Comment

  配置自定义规则时需谨慎，尽量避免与gfwlist产生冲突，或将一些本不需要代理的网址添加到代理列表

  规则优先级从高到底为: user-rule > user-rule-from > gfwlist
'''

_default_gfwlist_url = 'http://autoproxy-gfwlist.googlecode.com/svn/trunk/gfwlist.txt'

_pac_template = '''/**
 * genpac {version} http://jeeker.net/projects/genpac/
 * Generated: {generated}
 * GFWList Last-Modified: {gfwmodified}
 */

// proxy
var P = "{proxy}";

// user rules
var directUserRegexpList   = {direct_user_regexp_list};
var directUserWildcardList = {direct_User_Wildcard_List};
var proxyUserRegexpList    = {proxy_user_regexp_list};
var proxyUserWildcardList  = {proxy_user_wildcard_list};

// gfwlist rules
var directRegexpList   = {direct_regexp_list};
var directWildcardList = {direct_wildcard_list};
var proxyRegexpList    = {proxy_regexp_list};
var proxyWildcardList  = {proxy_wildcard_list};
{pac_funcs}
'''
_pac_funcs = '''
function FindProxyForURL(url, host) {
    var D = "DIRECT";

    var regExpMatch = function(url, pattern) {
        try { 
            return new RegExp(pattern).test(url); 
        } catch(ex) { 
            return false; 
        }
    };
    
    var i = 0;

    for (i in directUserRegexpList) {
        if(regExpMatch(url, directUserRegexpList[i])) return D;
    }

    for (i in directUserWildcardList) {
        if (shExpMatch(url, directUserWildcardList[i])) return D;
    }

    for (i in proxyUserRegexpList) {
        if(regExpMatch(url, proxyUserRegexpList[i])) return P;
    }

    for (i in proxyUserWildcardList) {
        if(shExpMatch(url, proxyUserWildcardList[i])) return P;
    }

    for (i in directRegexpList) {
        if(regExpMatch(url, directRegexpList[i])) return D;
    }

    for (i in directWildcardList) {
        if (shExpMatch(url, directWildcardList[i])) return D;
    }

    for (i in proxyRegexpList) {
        if(regExpMatch(url, proxyRegexpList[i])) return P;
    }

    for (i in proxyWildcardList) {
        if(shExpMatch(url, proxyWildcardList[i])) return P;
    }

    return D;
}
'''
_option_value_template ='''选项信息:
    proxy           : {}
    gfwlist url     : {}
    gfwlist proxy   : {}
    user rule       : {}
    user rule file  : {}
    config file     : {}
    output file     : {}
'''
_proxy_type_map = {
    'SOCKS'     : socks.PROXY_TYPE_SOCKS4,
    'SOCKS5'    : socks.PROXY_TYPE_SOCKS5,
    'PROXY'     : socks.PROXY_TYPE_HTTP,
}

class GenPAC(object):
    def __init__(
        self, 
        pac_proxy=None,
        gfwlist_url=_default_gfwlist_url, gfwlist_proxy=None,
        user_rules=[], user_rule_files=[],
        config_file=None,
        output_file=None,
        verbose=False
    ):
        self.verbose = verbose

        self.logger = logging.getLogger('genpac')
        if self.verbose:
            self.logger.setLevel(logging.DEBUG)
        stdout_handle = logging.StreamHandler(sys.stdout)
        stdout_handle.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(stdout_handle)

        self.logger.info('\ngenpac v{} {}({}) {}\n'.format(__version__, __author__, __author_email__, __project_page__))

        # 直接输入的参数优先级高于config文件
        self.configFile = config_file
        cfg = self.readConfig(self.configFile)
        self.pacProxy = pac_proxy if pac_proxy else cfg.get('pac_proxy', None)
        self.gfwlistURL = gfwlist_url if gfwlist_url else cfg.get('gfwlist_url', _default_gfwlist_url)
        self.gfwlistProxy = gfwlist_proxy if gfwlist_proxy else cfg.get('gfwlist_proxy', None)
        self.userRules = user_rules if user_rules else []
        self.userRuleFiles = user_rule_files if user_rule_files else cfg.get('user_rule_files', [])
        self.outputFile = output_file if output_file else cfg.get('output_file', None)

        self.gfwlistModified = ''
        self.gfwlistContent = ''
        self.userRulesContent = ''

    def generate(self):
        options = _option_value_template.format(
            self.pacProxy, self.gfwlistURL, self.gfwlistProxy,
            ' '.join(self.userRules) if self.userRules else 'None', 
            ' '.join(self.userRuleFiles) if self.userRuleFiles else 'None',
            self.configFile, self.outputFile
        )
        self.logger.info(options)
        #! pac的代理配置不检查准确性
        if not self.pacProxy:
            self.die('没有配置proxy')
        self.fetchGFWList()
        self.getUserRules()
        self.generatePACContent()

    def readConfig(self, config_file):
        def getv(c, k, d):
            try:
                return c.get('config', k).strip(' \'\t"')
            except Exception, e:
                return d
        if not config_file:
            return {}
        try:
            config_file = self.abspath(config_file)
            cfg = ConfigParser()
            cfg.readfp(open(config_file))
            user_rule_files = getv(cfg, 'user-rule-from', None)
            return {
                'pac_proxy'         : getv(cfg, 'proxy', None),
                'gfwlist_url'       : getv(cfg, 'gfwlist-url', _default_gfwlist_url),
                'gfwlist_proxy'     : getv(cfg, 'gfwlist-proxy', None),
                'user_rule_files'   : [user_rule_files] if user_rule_files else [], #user_rule_files 应该是个列表
                'output_file'       : getv(cfg, 'output', None)
            }
        except Exception, e:
            self.die('配置文件 {} 读取错误: {}'.format(config_file, e))

    def die(self, msg):
        self.logger.error(msg)
        sys.exit(1)

    # 下载gfwlist
    def fetchGFWList(self):
        self.logger.info('gfwlist获取中...')
        if self.gfwlistProxy:
            try:
                # 格式为 代理类型 [用户名:密码]@地址:端口 其中用户名和密码可选
                expr = re.compile('(PROXY|SOCKS|SOCKS5) (?:(.+):(.+)@)?(.+):(\d+)', re.IGNORECASE)
                ret = expr.match(self.gfwlistProxy)
                proxy_type = _proxy_type_map[ret.group(1).upper()]
                socks.setdefaultproxy(proxy_type, ret.group(4), int(ret.group(5)), True, ret.group(2), ret.group(3))
                socket.socket = socks.socksocket
            except Exception, e:
                self.die('gfwlist代理设置错误: {}'.format(e))

        if self.verbose:
            httpHandler = urllib2.HTTPHandler(debuglevel=1)
            httpsHandler = urllib2.HTTPSHandler(debuglevel=1)
            opener = urllib2.build_opener(httpHandler, httpsHandler)
            urllib2.install_opener(opener)

        try:
            res = urllib2.urlopen(self.gfwlistURL)
            self.gfwlistModified = res.info().getheader('last-modified')
            #! gfwlist文件内容的第一行内容是不符合语法规则的
            #! 手动将其注释掉
            self.gfwlistContent = '! {}'.format(base64.decodestring(res.read()))
        except Exception, e:
            self.die('gfwlist获取失败: {}'.format(e))
        self.logger.info('gfwlist已成功获取，更新时间: {}'.format(self.gfwlistModified))

    # 获取用户定义的规则
    def getUserRules(self):
        self.logger.info('获取用户自定义规则...')
        # userRules 优先级高于 userRuleFiles
        rules = ''
        rules = '\n'.join(self.userRules)
        for f in self.userRuleFiles:
            if not f:
                continue
            f = self.abspath(f)
            try:
                with open(f) as fp:
                    rules = '{}\n{}'.format(rules, fp.read())
            except Exception, e:
                self.die('读取用户自定义规则文件{}错误: {}'.format(f, e))
        self.userRulesContent = rules

    # 解析条件
    def parseRules(self, rules):
        direct_wildcard = []
        direct_regexp = []
        proxy_wildcard = []
        proxy_regexp = []
        for line in rules.splitlines():
            line = line.strip()
            # 忽略注释
            if not line or line.startswith('!'):
                continue
            is_direct = False
            is_regexp = True
            original_line = line
            # 例外
            if line.startswith('@@'):
                line = line[2:]
                is_direct = True
            # 正则表达式语法
            if line.startswith('/') and line.endswith('/'):
                line = line[1:-1]
            elif line.find('^') != -1:
                line = self.wildcardToRegexp(line)
                line = re.sub(r'\\\^', r'(?:[^\w\-.%\u0080-\uFFFF]|$)', line)
            elif line.startswith('||'):
                line = self.wildcardToRegexp(line[2:])
                # When using the constructor function, the normal string escape rules (preceding 
                # special characters with \ when included in a string) are necessary. 
                # For example, the following are equivalent:
                # re = new RegExp('\\w+')
                # re = /\w+/
                # via: http://aptana.com/reference/api/RegExp.html
                line = r'^[\\w\\-]+:\\/+(?!\\/)(?:[^\\/]+\\.)?' + line
            elif line.startswith('|') or line.endswith('|'):
                line = self.wildcardToRegexp(line)
                line = re.sub(r'^\\\|', '^', line, 1)
                line = re.sub(r'\\\|$', '$', line)
            else:
                is_regexp = False
            if not is_regexp:
                line = '*{}*'.format(line.strip('*'))
            if is_direct:
                direct_regexp.append(line)  if is_regexp else direct_wildcard.append(line)
            else:
                proxy_regexp.append(line) if is_regexp else proxy_wildcard.append(line)
        return [direct_regexp, direct_wildcard, proxy_regexp, proxy_wildcard]

    def generatePACContent(self):
        self.logger.info('解析规则并生成PAC内容...')
        gfwlist = self.parseRules(self.gfwlistContent)
        user = self.parseRules(self.userRulesContent)
        gfwlist = map(lambda d: self.convertListToJSArray(d), gfwlist)
        user = map(lambda d: self.convertListToJSArray(d), user)
        data = {
            'version'       : __version__,
            'generated'     : time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime()),
            'gfwmodified'   : self.gfwlistModified,
            'proxy'         : self.pacProxy,
            'pac_funcs'     : _pac_funcs,
            'direct_user_regexp_list'   : user[0],
            'direct_User_Wildcard_List' : user[1],
            'proxy_user_regexp_list'    : user[2],
            'proxy_user_wildcard_list'  : user[3],
            'direct_regexp_list'        : gfwlist[0],
            'direct_wildcard_list'      : gfwlist[1],
            'proxy_regexp_list'         : gfwlist[2],
            'proxy_wildcard_list'       : gfwlist[3]
        }
        pac = _pac_template.format(**data)
        with open('/Users/JinnLynn/Desktop/b64.txt', 'w') as fp:
            fp.write(base64.b64encode(pac))
        if not self.outputFile:
            print(pac)
            return
        output = self.abspath(self.outputFile)
        try:
            with open(output, 'w') as fp:
                fp.write(pac)
            print('PAC文件已生成: {}'.format(output))
        except Exception, e:
            self.die('写入文件{}失败: {}'.format(output, e))

    def wildcardToRegexp(self, pattern):
        pattern = re.sub(r'([\\\+\|\{\}\[\]\(\)\^\$\.\#])', r'\\\1', pattern);
        #pattern = re.sub(r'\*+', r'*', pattern)
        pattern = re.sub(r'\*', r'.*', pattern)
        pattern = re.sub(r'\？', r'.', pattern)
        return pattern;

    def convertListToJSArray(self, lst):
        lst = filter(lambda s: isinstance(s, basestring) and s, lst)
        array = "',\n    '".join(lst)
        if array:
            array = "\n    '{}'\n    ".format(array)
        return '[{}]'.format(array)

    def abspath(self, path):
        if path.startswith('~'):
            path = os.path.expanduser(path)
        return os.path.abspath(path)
        

class HelpAction(argparse.Action):
    def __init__(self, option_strings, dest=argparse.SUPPRESS, default=argparse.SUPPRESS, help=None):
        super(HelpAction, self).__init__(option_strings=option_strings, dest=dest, default=default, nargs=0, help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        print(_help)
        parser.exit()

def main():
    parser = argparse.ArgumentParser(
        prog='genpac',
        add_help=False      # 默认的帮助输出对中文似乎有问题，不使用
    )
    parser.add_argument('-p', '--proxy')
    parser.add_argument('--gfwlist-url', default=_default_gfwlist_url)
    parser.add_argument('--gfwlist-proxy')
    parser.add_argument('--user-rule', action='append')
    parser.add_argument('--user-rule-from', action='append')
    parser.add_argument('--output')
    parser.add_argument('--config-from')
    parser.add_argument('--verbose', action='store_true', default=False)
    parser.add_argument('-v', '--version', action='version', version='%(prog)s {}'.format(__version__))
    parser.add_argument('-h', '--help', action=HelpAction)
    args = parser.parse_args()
    GenPAC(
        args.proxy,
        gfwlist_url=args.gfwlist_url, gfwlist_proxy=args.gfwlist_proxy,
        user_rules=args.user_rule, user_rule_files=args.user_rule_from,
        config_file=args.config_from,
        output_file=args.output,
        verbose=args.verbose
    ).generate()

if __name__ == '__main__':
    main()