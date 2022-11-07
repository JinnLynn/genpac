from ..core import GenPAC
from .._compat import text_type
from .. import Namespace, TemplateFile, parse_rules
from ..util import error, replace_all


# decorator: 添加格式化器
def formater(name, **options):
    def decorator(fmt_cls):
        GenPAC.add_formater(name, fmt_cls, **options)
        return fmt_cls
    return decorator


class FmtBase(object):
    _name = ''
    _desc = None
    _default_tpl = None

    def __init__(self, *args, **kwargs):
        super(FmtBase, self).__init__()
        self.options = kwargs.get('options') or Namespace()

        self._update_orginal_rules(
            kwargs.get('user_rules') or [],
            kwargs.get('gfwlist_rules') or [])

    @classmethod
    def arguments(cls, parser):
        return parser.add_argument_group(title=cls._name.upper(),
                                         description=cls._desc or '')

    @classmethod
    def config(cls, options):
        pass

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
        return text_type(tpl).strip('\n') + '\n'

    def error(self, msg):
        error('{}格式生成错误: {}'.format(self._name.upper(), msg))

    def replace(self, text, replacements):
        return replace_all(text, replacements)

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

    @property
    def gfwed_domains(self):
        if self._gfwed_domains is None:
            self._gfwed_domains = list(
                set(self.rules[0][1] + self.rules[1][1]))
            self._gfwed_domains.sort()
        return self._gfwed_domains

    @property
    def ignored_domains(self):
        if self._ignored_domains is None:
            self._ignored_domains = list(
                set(self.rules[0][0] + self.rules[1][0]))
            self._ignored_domains.sort()
        return self._ignored_domains

    def _update_orginal_rules(self, user_rules, gfwlist_rules):
        self._orginal_user_rules = user_rules
        self._orginal_gfwlist_rules = gfwlist_rules
        self._rules = None
        self._precise_rules = None
        self._gfwed_domains = None
        self._ignored_domains = None
