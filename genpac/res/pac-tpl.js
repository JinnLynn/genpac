/**
 * genpac __VERSION__ https://github.com/JinnLynn/genpac
 * Generated: __GENERATED__
 * GFWList Last-Modified: __MODIFIED__
 * GFWList From: __GFWLIST_FROM__
 */

var proxy = '__PROXY__';
var rules = __RULES__;

var lastRule = '';

var regExpMatch = function(url, pattern) {
    try {
        return new RegExp(pattern).test(url); 
    } catch(ex) {
        return false; 
    }
};

var testURL = function(url, packs) {
    for (var i = 0; i < packs.length; i++) {
        for (var j = 0; j < packs[i].length; j++) {
            lastRule = packs[i][j];
            if ( (i % 2 == 0 && regExpMatch(url, lastRule)) 
                || (i % 2 != 0 && shExpMatch(url, lastRule)))
                return (i <= 1) ? 'DIRECT' : proxy;
        }
    }
    lastRule = '';
};

function FindProxyForURL(url, host) {
    for (var i = 0; i < rules.length; i++) {
        var ret = testURL(url, rules[i]);
        if (ret !== undefined)
            return ret;
    }
    return 'DIRECT';
}