from .base import formater
from .surge import FmtSurge


# Shadowrocket的代理规则与Surge是相同的
@formater('shadowrocket', desc='Shadowrocket(小火箭)代理规则', order=89)
class FmtShadowrocket(FmtSurge):
    pass
