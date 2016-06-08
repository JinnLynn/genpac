#!/usr/bin/env bash


build_test_js() {
    cat $1 >tmp/test.js
    echo >>tmp/test.js
    if [[ -z "$2" ]]; then
        echo "var precise = false;" >>tmp/test.js
    else
        echo "var precise = true;" >>tmp/test.js
    fi
    cat test/test-case.js >>tmp/test.js
}

echo_red() {
    echo -e "\033[31m$@\033[0m"
}

echo_green() {
    echo -e "\033[32m$@\033[0m"
}

cd .. 
PYTHONPATH=.
[[ -d tmp ]] && rm -rf tmp
mkdir -p tmp
cp test/gfwlist.txt tmp/

coverage erase

coverage run -a -m genpac -h && \
coverage run -a -m genpac --init=tmp/init && \
coverage run -a -m genpac -p "PROXY" && \
coverage run -a -m genpac -p "PROXY" -z && \
coverage run -a -m genpac -p "PROXY" -P && \
coverage run -a -m genpac -p "PROXY" -P -z && \
coverage run -a -m genpac -p "PROXY" --gfwlist-local=tmp/gfwlist.txt --gfwlist-url=- && \
coverage run -a -m genpac -p "PROXY" --gfwlist-local=tmp/gfwlist.txt --update-gfwlist-local && \
coverage run -a -m genpac -p "PROXY" --gfwlist-url=- && \
coverage run -a -m genpac -p "PROXY" --gfwlist-disabled && \
coverage run -a -m genpac -p "PROXY" --config-from=test/config-empty.ini && \
coverage run -a -m genpac -p "PROXY" --config-from=test/config.ini && \
coverage run -a -m genpac -p "PROXY" --gfwlist-local=tmp/gfwlist.txt --gfwlist-url=- --user-rule="@@sina.com" --user-rule="||twitter.com" && \
coverage run -a -m genpac -p "PROXY" --gfwlist-local=tmp/gfwlist.txt --gfwlist-url=- --user-rule-from="test/user-rules-direct.txt,test/user-rules-proxy.txt" --user-rule-from="," && \
coverage run -a -m genpac -p "PROXY" --gfwlist-local=tmp/gfwlist.txt --gfwlist-url=- --config-from=test/config.ini -o tmp/pac.js && \
coverage run -a -m genpac -p "PROXY" --gfwlist-local=tmp/gfwlist.txt --gfwlist-url=- --config-from=test/config.ini -z -o tmp/pac-compress.js && \
coverage run -a -m genpac -p "PROXY" --gfwlist-local=tmp/gfwlist.txt --gfwlist-url=- --config-from=test/config.ini -P -o tmp/pac-precise.js && \
coverage run -a -m genpac -p "PROXY" --gfwlist-local=tmp/gfwlist.txt --gfwlist-url=- --config-from=test/config.ini -P -z -o tmp/pac-precise-compress.js && {
    # 出错的测试
    coverage run -a -m genpac
    echo n | coverage run -a -m genpac --init=tmp/init
    coverage run -a -m genpac -p "PROXY" --gfwlist-url=nonexistent-url
    coverage run -a -m genpac -p "PROXY" --gfwlist-disabled -o nonexistent/path
    coverage run -a -m genpac -p "PROXY" --gfwlist-disabled -c nonexistent/path
    coverage run -a -m genpac -p "PROXY" --gfwlist-disabled --user-rule-from=nonexistent/path
    coverage run -a -m genpac -p "PROXY" --gfwlist-proxy="error proxy"
    # gfwlist proxy test 可能出错
    coverage run -a -m genpac -p "PROXY" --gfwlist-proxy="SOCKS5 127.0.0.1:9527" && echo_green "gfwlist-proxy socks5 ok" || echo_red "gfwlist-proxy socks5 fail"
    coverage run -a -m genpac -p "PROXY" --gfwlist-proxy="PROXY 127.0.0.1:9580" && echo_green "gfwlist-proxy http ok" || echo_red "gfwlist-proxy http fail"
    rm -rf tmp/init
    # 让这个测试块返回正确
    echo
} && \
build_test_js tmp/pac.js && \
node tmp/test.js && \
build_test_js tmp/pac-compress.js && \
node tmp/test.js && \
build_test_js tmp/pac-precise.js 1 && \
node tmp/test.js && \
build_test_js tmp/pac-precise-compress.js 1 && \
node tmp/test.js && \
coverage report --include="genpac/*" && \
coverage html && \
rm -rf tmp

