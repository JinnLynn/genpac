#!/usr/bin/env bash
test_dir="tests"
tmp=$test_dir/tmp
test_case=$test_dir/etc/test-case.js
tmp_test=$tmp/test.js

build_test_js() {
    cat $1 >$tmp_test
    echo >>$tmp_test
    if [[ -z "$2" ]]; then
        echo "var precise = false;" >>$tmp_test
    else
        echo "var precise = true;" >>$tmp_test
    fi
    cat $test_case >>$tmp_test
}

build_test_js $tmp/pac.js && \
node $tmp/test.js && \
build_test_js $tmp/pac-compress.js && \
node $tmp/test.js && \
build_test_js $tmp/pac-precise.js 1 && \
node $tmp/test.js && \
build_test_js $tmp/pac-compress-precise.js 1 && \
node $tmp/test.js && \
rm -rf $tmp
