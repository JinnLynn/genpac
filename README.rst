GenPAC
===========

Generate PAC file from gfwlist, custom rules supported. 

Usage
~~~~~

::

    pip install genpac

    genpac [-h|--help] [-v|version]
           [-p PROXY|--proxy=PROXY]
           [--gfwlist-url=URL] [--gfwlist-proxy=PROXY]
           [--user-rule=RULE] [--user-rule-from=FILE]
           [--config-from=FILE] [--output=FILE]
                  
    可选参数:
      -h, --help                显示帮助内容
      -v, --version             显示版本信息
      -p PROXY, --proxy=PROXY   PAC文件中使用的代理信息，如:
                                  SOCKS 127.0.0.1:8080
                                  SOCKS5 127.0.0.1:8080; SOCKS 127.0.0.1:8080
                                  PROXY 127.0.0.1:8080
      --gfwlist-url=URL         gfwlist地址，一般不需要更改，默认: 
                                  http://autoproxy-gfwlist.googlecode.com/svn/trunk/gfwlist.txt
      --gfwlist-proxy=PROXY     获取gfwlist时的代理设置，如果你可以正常访问gfwlist，则无必要使用该选项
                                格式为 "代理类型 [用户名:密码]@地址:端口" 其中用户名和密码可选，如: 
                                  SOCKS5 127.0.0.1:8080
                                  SOCKS5 username:password@127.0.0.1:8080
      --user-rule=RULE          自定义规则，该选项允许重复使用，如:
                                  --user-rule="@@sina.com"
                                  --user-rule="||youtube.com"
      --user-rule-from=FILE     从文件中读取自定义规则，该选项允许重复使用
      --config-from=FILE        从文件中读取配置信息
      --output=FILE             输出生成的文件，如果没有此选项，将直接打印结果

