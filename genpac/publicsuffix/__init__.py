"""Public Suffix List module for Python.
"""

import codecs
from pkg_resources import resource_stream, get_distribution
import warnings

try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request

PUBLIC_SUFFIX_LIST_URL = 'http://publicsuffix.org/list/public_suffix_list.dat'


def fetch():
    """Downloads the latest public suffix list from publicsuffix.org.

    Returns a file object containing the public suffix list.
    """

    ua = 'Python-publicsuffix/%s' % (get_distribution(__name__).version)
    req = Request(PUBLIC_SUFFIX_LIST_URL, headers={'User-Agent': ua})
    res = urlopen(req)

    try:
        encoding = res.headers.get_content_charset()
    except AttributeError:
        encoding = res.headers.getparam('charset')

    f = codecs.getreader(encoding)(res)

    return f


class PublicSuffixList(object):
    def __init__(self, input_file=None):
        """Reads and parses public suffix list.

        input_file is a file object or another iterable that returns
        lines of a public suffix list file.

        The file format is described at http://publicsuffix.org/list/
        """

        if input_file is None:
            warnings.warn(
                ("Using the built-in public suffix ",
                    "list is deprecated. Please use input_file."),
                DeprecationWarning, 2)
            input_stream = resource_stream(__name__, 'public_suffix_list.dat')
            input_file = codecs.getreader('utf8')(input_stream)
            do_close = True
        else:
            do_close = False

        root = self._build_structure(input_file)
        self.root = self._simplify(root)

        if do_close:
            input_file.close()

    def _find_node(self, parent, parts):
        if not parts:
            return parent

        if len(parent) == 1:
            parent.append({})

        assert len(parent) == 2
        negate, children = parent

        child = parts.pop()

        child_node = children.get(child, None)

        if not child_node:
            children[child] = child_node = [0]

        return self._find_node(child_node, parts)

    def _add_rule(self, root, rule):
        if rule.startswith('!'):
            negate = 1
            rule = rule[1:]
        else:
            negate = 0

        parts = rule.split('.')
        self._find_node(root, parts)[0] = negate

    def _simplify(self, node):
        if len(node) == 1:
            return node[0]

        return (
            node[0], dict((k, self._simplify(v)) for (k, v) in node[1].items())
            )

    def _build_structure(self, fp):
        root = [0]

        for line in fp:
            line = line.strip()
            if line.startswith('//') or not line:
                continue

            self._add_rule(root, line.split()[0].lstrip('.'))

        return root

    def _lookup_node(self, matches, depth, parent, parts):
        if parent in (0, 1):
            negate = parent
            children = None
        else:
            negate, children = parent

        matches[-depth] = negate

        if depth < len(parts) and children:
            for name in ('*', parts[-depth]):
                child = children.get(name, None)
                if child is not None:
                    self._lookup_node(matches, depth+1, child, parts)

    def get_public_suffix(self, domain):
        """get_public_suffix("www.example.com") -> "example.com"

        Calling this function with a DNS name will return the
        public suffix for that name.

        Note that for internationalized domains the list at
        http://publicsuffix.org uses decoded names, so it is
        up to the caller to decode any Punycode-encoded names.
        """

        parts = domain.lower().strip('.').split('.')
        hits = [None] * len(parts)

        self._lookup_node(hits, 1, self.root, parts)

        for i, what in enumerate(hits):
            if what is not None and what == 0:
                return '.'.join(parts[i:])
