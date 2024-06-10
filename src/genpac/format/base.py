import importlib
from os import path
import glob

from ..core import GenPAC, register_option
from .. import TemplateFile, parse_rules
from ..util import error, replace_all, Namespace


def _import_all_format():
    for f in glob.glob(path.join(path.dirname(__file__), "*.py")):
        f_bn = path.basename(f)
        if not path.isfile(f) or f_bn in ['__init__.py', 'base.py']:
            continue
        importlib.import_module(f'.{f_bn[:-3]}', __package__)


# decorator: 添加格式化器
def formater(name, **options):
    def decorator(fmt_cls):
        GenPAC.add_formater(name, fmt_cls, **options)
        return fmt_cls
    return decorator


class FmtBase(object):
    _name = ''
    _desc = None
    _parser = None
    _options = {}

    _default_tpl = None

    def __init__(self, *args, **kwargs):
        super(FmtBase, self).__init__()
        self.options = kwargs.get('options') or Namespace()
        self.generator = kwargs.get('generator')

        self._update_orginal_rules(
            kwargs.get('user_rules') or [],
            kwargs.get('gfwlist_rules') or [])

    @classmethod
    def prepare(cls, parser):
        cls._parser = parser.add_argument_group(title=cls._name.upper(),
                                                description=cls._desc or '')

    @classmethod
    def register_option(cls, *args, **kwargs):
        register_option(cls._parser, cls._options, *args, **kwargs)

    def pre_generate(self):
        return True

    def generate(self, replacements):
        return self.replace(self.tpl, replacements)

    def post_generate(self):
        pass

    @property
    def tpl(self):
        tpl = TemplateFile(self.options.template) if self.options.template else \
            self._default_tpl
        return str(tpl).strip('\n') + '\n'

    def error(self, msg):
        error(f'{self._name.upper()}格式生成错误: {msg}')

    def replace(self, text, replacements):
        return replace_all(text, replacements)

    # RETURN:
    # [0][0]: user.direct    [0][1]: user.proxy
    # [1][0]: gfwlist.direct [1][1]: gfwlist.proxy
    @property
    def rules(self):
        if self._rules is None:
            self._rules = [parse_rules(self._orginal_user_rules),
                           parse_rules(self._orginal_gfwlist_rules)]
        return self._rules

    @property
    def precise_rules(self):
        if self._precise_rules is None:
            self._precise_rules = [
                parse_rules(self._orginal_user_rules, True),
                parse_rules(self._orginal_gfwlist_rules, True)]
        return self._precise_rules

    # 优先级: user.proxy > user.direct > gfwlist.proxy > gfwlist.direct
    @property
    def gfwed_domains(self):
        if isinstance(self._gfwed_domains, list):
            return self._gfwed_domains
        # 1. gfwlist.proxy
        # 2. 过滤掉user.direct中包含的
        self._gfwed_domains = [d for d in self.rules[1][1] if d not in self.rules[0][0]]
        # 3. 合并上 user.proxy
        # 4. 去重
        self._gfwed_domains = list(set(self._gfwed_domains + self.rules[0][1]))
        self._gfwed_domains.sort()
        return self._gfwed_domains

    # 优先级: user.proxy > user.direct > gfwlist.proxy > gfwlist.direct
    @property
    def ignored_domains(self):
        if isinstance(self._ignored_domains, list):
            return self._ignored_domains
        # 1. gfwlist.direct
        # 2. 过滤掉gfwlist.proxy包含的
        self._ignored_domains = [d for d in self.rules[1][0] if d not in self.rules[1][1]]
        # 3. 合并上 user.direct
        self._ignored_domains += self.rules[0][0]
        # 4. 过滤到 user.proxy 包含的
        self._ignored_domains = [d for d in self._ignored_domains if d not in self.rules[0][1]]
        # 5. 去重
        self._ignored_domains = list(set(self._ignored_domains))
        self._ignored_domains.sort()
        return self._ignored_domains

    def _update_orginal_rules(self, user_rules, gfwlist_rules):
        self._orginal_user_rules = user_rules
        self._orginal_gfwlist_rules = gfwlist_rules
        self._rules = None
        self._precise_rules = None
        self._gfwed_domains = None
        self._ignored_domains = None