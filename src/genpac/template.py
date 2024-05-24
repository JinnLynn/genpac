from .util import get_resource_path, read_file


# 模板文件
# is_buildin == True时为内建模板文件，在脚本源码目录下寻找
class TemplateFile(object):
    def __init__(self, path, is_buildin=False):
        self.tpl_file = get_resource_path(path) if is_buildin else path

    def __str__(self):
        content = read_file(self.tpl_file, fail_msg='读取自定义模板文件{path}失败')
        return content.strip('\n')

# 去除文本模板的前后换行符
# for name in dir():
#     if name.isupper() and isinstance(vars()[name], str):
#         vars()[name] = vars()[name].strip('\n')
