#!/usr/bin/env python
# -*- coding: utf-8 -*-

##
# PAC Generator 0.1a
# Description: 自动代理配置(Proxy Auto-config)文件生成器，基于gfwlist。
#              更多信息访问项目页面
# Author: JinnLynn http://jeeker.net
# Project Page: http://jeeker.net/projects/genpac/
# Source: https://github.com/JinnLynn/GenPAC
# License: CC BY 3.0 
#          http://creativecommons.org/licenses/by/3.0/
## 

# gfwlist地址
gfwlistUrl="http://autoproxy-gfwlist.googlecode.com/svn/trunk/gfwlist.txt"

# 获取GFWList的代理设置，与PAC内的配置可能不同
# 如果你可以正常访问gfwlistUrl，可以设置为不使用代理
# gfwProxyType 0 不使用代理; 1 SOCKS4; 2 SOCKS5; 3 HTTP
gfwProxyType = 2
gfwProxyHost = '127.0.0.1'
gfwProxyPort = 9527
gfwProxyUsr  = None
gfwProxyPwd  = None

# PAC的代理配置
# 注意：如果是在MAC下的SOCKS代理，必须设置成SOCKS5
# proxyType 1 SOCKS e.g. SOCKS 127.0.0.1:9527
#           2 SOCKS5 e.g. SOCKS5 127.0.0.1:9527; SOCKS 127.0.0.1:9527
#           3 HTTP e.g. PROXY 127.0.0.1:9527
# 默认 SOCKS5
proxyType = 2
proxyHost = '127.0.0.1'
proxyPort = 9527

# 生成的PAC文件名
pacFile = "AutoProxy.pac"

# ********************************************************************** #

VERSION = '0.1a'
DEBUGMODE = False

import sys, os, base64, re

def fetchGFWList():
    import socks, socket, urllib2
    if (gfwProxyType == socks.PROXY_TYPE_SOCKS4) or (gfwProxyType == socks.PROXY_TYPE_SOCKS5) or (gfwProxyType == socks.PROXY_TYPE_HTTP):
        socks.setdefaultproxy(gfwProxyType, gfwProxyHost, gfwProxyPort, True, gfwProxyUsr, gfwProxyPwd)
        socket.socket = socks.socksocket

    if DEBUGMODE:
        httpHandler = urllib2.HTTPHandler(debuglevel=1)
        httpsHandler = urllib2.HTTPSHandler(debuglevel=1)
        opener = urllib2.build_opener(httpHandler, httpsHandler)
        urllib2.install_opener(opener)

    try:
        response = urllib2.urlopen(gfwlistUrl)
        content = response.read()
    except Exception, e:
        return False, e
    return True, content

def wildcardToRegexp(pattern):
    pattern = re.sub(r"([\\\+\|\{\}\[\]\(\)\^\$\.\#])", r"\\\1", pattern);
    #pattern = re.sub(r"\*+", r"*", pattern)
    pattern = re.sub(r"\*", r".*", pattern)
    pattern = re.sub(r"\？", r".", pattern)
    return pattern;

def parseRuleList(ruleList):
    directWildcardList = []
    directRegexpList = []
    proxyWildcardList = []
    proxyRegexpList = []
    for line in ruleList.splitlines()[1:]:
        # 忽略注释
        if (len(line) == 0) or (line.startswith("!")) or (line.startswith("[")):
            continue

        isDirect = False
        isRegexp = True

        origin_line = line

        # 例外
        if line.startswith("@@"):
            line = line[2:]
            isDirect = True

        # 正则表达式语法
        if line.startswith("/") and line.endswith("/"):
            line = line[1:-1]
        elif line.find("^") != -1:
            line = wildcardToRegexp(line)
            line = re.sub(r"\\\^", r"(?:[^\w\-.%\u0080-\uFFFF]|$)", line)
        elif line.startswith("||"):
            line = wildcardToRegexp(line[2:])
            # When using the constructor function, the normal string escape rules (preceding 
            # special characters with \ when included in a string) are necessary. 
            # For example, the following are equivalent:
            # re = new RegExp("\\w+")
            # re = /\w+/
            # via: http://aptana.com/reference/api/RegExp.html
            line = r"^[\\w\\-]+:\\/+(?!\\/)(?:[^\\/]+\\.)?" + line
        elif line.startswith("|") or line.endswith("|"):
            line = wildcardToRegexp(line)
            line = re.sub(r"^\\\|", "^", line, 1)
            line = re.sub(r"\\\|$", "$", line)
        else:
            isRegexp = False

        if not isRegexp:
            if not line.startswith("*"):
                line = "*" + line
            if not line.endswith("*"):
                line += "*"

        if isDirect:
            if isRegexp: 
                directRegexpList.append(line) 
            else: 
                directWildcardList.append(line)
        else:
            if isRegexp: 
                proxyRegexpList.append(line) 
            else: 
                proxyWildcardList.append(line)

        if DEBUGMODE:
            with open('tmp/rule.txt', 'a') as f:
                f.write("%s\n\t%s\n\n" % (origin_line, line) )

    return directRegexpList, directWildcardList, proxyRegexpList, proxyWildcardList

def generateProxyVar():
    host = '%s:%d' % (proxyHost, proxyPort) 
    if proxyType == 1:
        return 'SOCKS %s' % host
    elif proxyType == 3:
        return 'PROXY %s' % host
    else:
        return 'SOCKS5 %s; SOCKS %s' % (host, host)

def convertListToJSArray(list):
    array = ''
    indent = '    '
    for list_item in list:
        if len(array) != 0:
            array +=",\n"
        array += "%s'%s'" % (indent, list_item)
    if len(array) != 0:
        array = "\n" + array + "\n" + indent;
    return "[" + array + "]"

def generatePacRules(gfwlist):
    gfwlist = base64.decodestring(gfwlist)
    if DEBUGMODE:
        with open('tmp/gfwlist.txt', 'w') as f:
            f.write(gfwlist)

    directRegexpList, directWildcardList, proxyRegexpList, proxyWildcardList = parseRuleList(gfwlist)

    rules = '''    var directRegexpList   = %s;
    var directWildcardList = %s;
    var proxyRegexpList    = %s;
    var proxyWildcardList  = %s;
    ''' % ( convertListToJSArray(directRegexpList), 
            convertListToJSArray(directWildcardList), 
            convertListToJSArray(proxyRegexpList), 
            convertListToJSArray(proxyWildcardList)
          )
    return rules

def CreatePacFile(gfwlist):
    pacContent = '''/**
 * Generated by GenPAC %(ver)s
 * Author: JinnLynn http://jeeker.net
 * Project Page: http://jeeker.net/projects/genpac/
 */

function regExpMatch(url, pattern) {
    try { return new RegExp(pattern).test(url); } catch(ex) { return false; }
}

function FindProxyForURL(url, host) {
    var P = "%(proxy)s";
    var D = "DIRECT";
    var i = 0;
    var length = 0;
%(rules)s
    // gfwlist Rules
    length = directRegexpList.length;
    for (i = 0; i < length; i++)
    {
        if(regExpMatch(url, directRegexpList[i])) return D;
    }

    length = directWildcardList.length;
    for (i = 0; i < length; i++)
    {
        if (shExpMatch(url, directWildcardList[i])) return D;
    }

    length = proxyRegexpList.length;
    for (i = 0; i < length; i++)
    {
        if(regExpMatch(url, proxyRegexpList[i])) return P;
    }

    length = proxyWildcardList.length;
    for (i = 0; i < length; i++)
    {
        if(shExpMatch(url, proxyWildcardList[i])) return P;
    }

    return D;
}
'''
    result = { 'ver': VERSION,
               'proxy': generateProxyVar(),
               'rules': generatePacRules(gfwlist),
              }
    with open(pacFile, 'w') as handle:
        handle.write(pacContent % result)


if __name__ == "__main__":
    print '''/** 
 * PAC Generator %s by JinnLynn http://jeeker.net
 */''' % VERSION

    if not os.path.exists('tmp') or not os.path.isdir('tmp'):
        os.mkdir('tmp')
    #os.remove('tmp/*')
    os.system("rm -rf tmp/*")

    print "正在获取GFWList %s ..." % gfwlistUrl
    res, content = fetchGFWList()
    if res == False:
        print "GFWList获取失败，请检查相关内容是否配置正确。"
        print "错误信息: %s" % content
    else:
        print "正在生成 %s ..." % pacFile
        CreatePacFile(content)
        print "一切就绪。"