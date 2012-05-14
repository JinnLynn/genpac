#!/usr/bin/env python
# -*- coding: utf-8 -*-

##
# PAC Generator 0.2.1
# Description: 自动代理配置(Proxy Auto-config)文件生成器，基于gfwlist，支持自定义规则。
#              更多信息访问项目页面
# Author: JinnLynn http://jeeker.net
# Project Page: http://jeeker.net/projects/genpac/
# Source: https://github.com/JinnLynn/GenPAC
# License: CC BY 3.0 
#          http://creativecommons.org/licenses/by/3.0/
##

# ********************************************************************** #

VERSION = '0.2.1'

defaultConfig = {
               'gfwUrl'       : 'http://autoproxy-gfwlist.googlecode.com/svn/trunk/gfwlist.txt',
               'gfwProxyType' : 2,
               'gfwProxyHost' : '127.0.0.1',
               'gfwProxyPort' : 9527,
               'gfwProxyUsr'  : None,
               'gfwProxyPwd'  : None,
               'pacProxyType' : 2,
               'pacProxyHost' : '127.0.0.1',
               'pacProxyPort' : 9527,
               'pacFilename'  : 'AutoProxy.pac',
               'DebugMode'    : False,
               'JSVersion'    : True
                }

gfwlistContent = ''
gfwlistModified = ''
config = {}

import sys, os, base64, re, ConfigParser, time

def parseConfig():
    global defaultConfig, config
    cf = ConfigParser.ConfigParser(defaultConfig);
    cf.read('config.txt')

    try:
        config = {
                   'gfwUrl'       : cf.get('config', 'gfwUrl'),
                   'gfwProxyType' : cf.getint('config', 'gfwProxyType'),
                   'gfwProxyHost' : cf.get('config', 'gfwProxyHost'),
                   'gfwProxyPort' : cf.getint('config', 'gfwProxyPort'),
                   'gfwProxyUsr'  : cf.get('config', 'gfwProxyUsr'),
                   'gfwProxyPwd'  : cf.get('config', 'gfwProxyPwd'),
                   'pacProxyType' : cf.getint('config', 'pacProxyType'),
                   'pacProxyHost' : cf.get('config', 'pacProxyHost'),
                   'pacProxyPort' : cf.getint('config', 'pacProxyPort'),
                   'pacFilename'  : cf.get('config', 'pacFilename'),
                   'DebugMode'    : cf.getboolean('config', 'DebugMode'),
                   'JSVersion'    : cf.getboolean('config', 'JSVersion')
                    }
    except Exception, e:
        print e

def printConfigInfo():
    print "配置信息: "
    print 'GFWList Proxy: Type: %s, Host: %s, Port: %s , Usr: %s, Pwd: %s' % (config['gfwProxyType'], 
                                                                              config['gfwProxyHost'], config['gfwProxyPort'], 
                                                                              config['gfwProxyUsr'], config['gfwProxyPwd'])
    print "PAC Proxy String: %s" % generateProxyVar()

def fetchGFWList():
    global gfwlistContent, gfwlistModified
    import socks, socket, urllib2
    gfwProxyType = config['gfwProxyType']
    if (gfwProxyType == socks.PROXY_TYPE_SOCKS4) or (gfwProxyType == socks.PROXY_TYPE_SOCKS5) or (gfwProxyType == socks.PROXY_TYPE_HTTP):
        socks.setdefaultproxy(gfwProxyType, config['gfwProxyHost'], config['gfwProxyPort'], True, config['gfwProxyUsr'], config['gfwProxyPwd'])
        socket.socket = socks.socksocket

    if config['DebugMode']:
        httpHandler = urllib2.HTTPHandler(debuglevel=1)
        httpsHandler = urllib2.HTTPSHandler(debuglevel=1)
        opener = urllib2.build_opener(httpHandler, httpsHandler)
        urllib2.install_opener(opener)

    try:
        response = urllib2.urlopen(config['gfwUrl'])
        gfwlistModified = response.info().getheader('last-modified')
        gfwlistContent = response.read()
    except Exception, e:
        return False, e
    return True, None

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

        if config['DebugMode']:
            with open('tmp/rule.txt', 'a') as f:
                f.write("%s\n\t%s\n\n" % (origin_line, line) )

    return directRegexpList, directWildcardList, proxyRegexpList, proxyWildcardList

def generateProxyVar():
    host = '%s:%d' % (config['pacProxyHost'], config['pacProxyPort']) 
    if config['pacProxyType'] == 1:
        return 'SOCKS %s' % host
    elif config['pacProxyType'] == 3:
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

def parseGFWListRules():
    global gfwlistContent
    gfwlist = base64.decodestring(gfwlistContent)
    if config['DebugMode']:
        with open('tmp/gfwlist.txt', 'w') as f:
            f.write(gfwlist)

    return parseRuleList(gfwlist)

def parseUserRules():
    directUserRegexpList = []
    directUserWildcardList = []
    proxyUserRegexpList = []
    proxyUserWildcardList = []
    try:
        with open('user-rules.txt') as f:
            directUserRegexpList, directUserWildcardList, proxyUserRegexpList, proxyUserWildcardList = parseRuleList(f.read())
    except Exception, e:
        pass
    
    return directUserRegexpList, directUserWildcardList, proxyUserRegexpList, proxyUserWildcardList

def generatePACRuls(userRules, gfwListRules):
    directRegexpList, directWildcardList, proxyRegexpList, proxyWildcardList = parseGFWListRules()
    directUserRegexpList, directUserWildcardList, proxyUserRegexpList, proxyUserWildcardList = parseUserRules()

    rules = '''    //User Rules
    var directUserRegexpList   = %s;
    var directUserWildcardList = %s;
    var proxyUserRegexpList    = %s;
    var proxyUserWildcardList  = %s;

    //gfwlist Rules
    var directRegexpList   = %s;
    var directWildcardList = %s;
    var proxyRegexpList    = %s;
    var proxyWildcardList  = %s;

    ''' % ( convertListToJSArray(directUserRegexpList), 
            convertListToJSArray(directUserWildcardList), 
            convertListToJSArray(proxyUserRegexpList), 
            convertListToJSArray(proxyUserWildcardList),
            convertListToJSArray(directRegexpList), 
            convertListToJSArray(directWildcardList), 
            convertListToJSArray(proxyRegexpList), 
            convertListToJSArray(proxyWildcardList)
          )
    return rules


def CreatePacFile(gfwlistRules, userRules):
    pacContent = '''/**
 * Generated by GenPAC %(ver)s
 * Author: JinnLynn http://jeeker.net
 * Project Page: http://jeeker.net/projects/genpac/
 * Generated: %(generated)s
 * GFWList Last Modified: %(gfwmodified)s
 */

function regExpMatch(url, pattern) {
    try { 
        return new RegExp(pattern).test(url); 
    } catch(ex) { 
        return false; 
    }
}

function FindProxyForURL(url, host) {
    var P = "%(proxy)s";
    var D = "DIRECT";
%(rules)s
    var i = 0;
    var length = 0;

    length = directUserRegexpList.length;
    for (i = 0; i < length; i++) {
        if(regExpMatch(url, directUserRegexpList[i])) return D;
    }

    length = directUserWildcardList.length;
    for (i = 0; i < length; i++) {
        if (shExpMatch(url, directUserWildcardList[i])) return D;
    }

    length = proxyUserRegexpList.length;
    for (i = 0; i < length; i++) {
        if(regExpMatch(url, proxyUserRegexpList[i])) return P;
    }

    length = proxyUserWildcardList.length;
    for (i = 0; i < length; i++) {
        if(shExpMatch(url, proxyUserWildcardList[i])) return P;
    }

    length = directRegexpList.length;
    for (i = 0; i < length; i++) {
        if(regExpMatch(url, directRegexpList[i])) return D;
    }

    length = directWildcardList.length;
    for (i = 0; i < length; i++) {
        if (shExpMatch(url, directWildcardList[i])) return D;
    }

    length = proxyRegexpList.length;
    for (i = 0; i < length; i++) {
        if(regExpMatch(url, proxyRegexpList[i])) return P;
    }

    length = proxyWildcardList.length;
    for (i = 0; i < length; i++) {
        if(shExpMatch(url, proxyWildcardList[i])) return P;
    }

    return D;
}
'''
    result = { 'ver':       VERSION,
               'generated': time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime()),
               'gfwmodified': gfwlistModified,
               'proxy':     generateProxyVar(),
               'rules':     generatePACRuls(userRules, gfwlistRules)
              }
    pacContent = pacContent % result
    with open(config['pacFilename'], 'w') as handle:
        handle.write(pacContent)

    if config['JSVersion']:
        with open('test/genpac.js', 'w') as js:
            js.write(pacContent)

if __name__ == "__main__":

    #更改工作目录为脚本所在目录
    os.chdir(sys.path[0])

    print '''/** 
 * PAC Generator %s by JinnLynn http://jeeker.net
 */''' % VERSION

    if not os.path.exists('tmp') or not os.path.isdir('tmp'):
        os.mkdir('tmp')
    #os.remove('tmp/*')
    os.system("rm -rf tmp/*")

    parseConfig()

    printConfigInfo()

    print "正在获取GFWList %s ..." % config['gfwUrl']
    res, errorInfo = fetchGFWList()
    if res == False:
        print "GFWList获取失败，请检查相关内容是否配置正确。"
        print "错误信息: %s" % errorInfo
    else:
        print "GFWList[Last-Modified: %s]已获取。" % gfwlistModified
        print '正在解析 GFWList Rules ...'
    
    # 无论gfwlist是否获取成功，都要解析，否则PAC文件有错，只是获取失败时解析的是空数据
    gfwlistRules = parseGFWListRules()

    print '正在解析 User Rules ...'
    userRules = parseUserRules()

    print "正在生成 %s ..." % config['pacFilename']
    CreatePacFile(userRules, gfwlistRules)
    
    print "一切就绪。"