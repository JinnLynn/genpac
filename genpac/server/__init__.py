__all__ = ['create_app', 'FmtDomains', 'run']

try:
    from .core import create_app, FmtDomains, run
except ModuleNotFoundError as e:
    from ..util import exit_error
    exit_error(f'genpac.server未正确安装，请使用`pip install genpac[server]`安装所需模块。{e}')
