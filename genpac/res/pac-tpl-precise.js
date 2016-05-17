/**
 * genpac __VERSION__ https://github.com/JinnLynn/genpac
 * Generated: __GENERATED__
 * GFWList Last-Modified: __MODIFIED__
 * GFWList From: __GFWLIST_FROM__
 */

var proxy = '__PROXY__';
var rules = __RULES__;

var lastRule = '';

function FindProxyForURL(url, host) {
    for (var i = 0; i < rules.length; i++) {
        var ret = testURL(url, i);
        if (ret !== undefined)
            return ret;
    }
    return 'DIRECT';
}

function testURL(url, index) {
    for (var i = 0; i < rules[index].length; i++) {
        for (var j = 0; j < rules[index][i].length; j++) {
            lastRule = rules[index][i][j];
            if ( (i % 2 == 0 && regExpMatch(url, lastRule)) 
                || (i % 2 != 0 && shExpMatch(url, lastRule)))
                return (i <= 1) ? 'DIRECT' : proxy;
        }
    }
    lastRule = '';
};

function regExpMatch(url, pattern) {
    try {
        return new RegExp(pattern).test(url); 
    } catch(ex) {
        return false; 
    }
};
