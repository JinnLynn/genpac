from flask import current_app

from .. import formater, FmtBase


@formater('genpac-server-domains')
class FmtDomains(FmtBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate(self, replacements):
        gfwed = [f'p,{s}' for s in self.gfwed_domains]
        ignored = [f'd,{s}' for s in self.ignored_domains]
        return '\n'.join(gfwed + ignored).strip()

    def post_generate(self):
        try:
            current_app.extensions['genpac'].domains_outdate = True
        except Exception:
            pass
