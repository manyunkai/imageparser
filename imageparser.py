# -*-coding:utf-8 -*-
'''
Created on 2013-6-10
@author: Danny<manyunkai@hotmail.com>
DannyWork Project
'''

import os

from imageutils import ImageIOTools, ImageTrimTools, get_image_dimensions


class ImageParser(object):
    """
    一个简单的图片检测与处理类

    基本使用方法：
        实例化时，需要两个参数：
            1. config配置；
            2. 图片来源，如果来源于上传，则传给from_buffer；
               如果来源于本地文件，则传给from_file。
        然后调用is_valid()检测图片是否有效，有效返回True，否则返回False。
        在验证成功后，可以调用save()自动保存所有尺寸的图片，
        save接收三个可选参数：
            filename：要保存的文件名，默认为原文件名；
            format：保存的格式，默认为原格式；
            save_origin：布尔值，指定是否保存原图，默认为True。

    config配置示例与说明：
        config以字典形式组成，limits用于验证、origin为原图处理、dimensions为各尺寸定义；
        每个部分均为可选。

        PHOTO_CONF = {
            'limits': {
                'formats': ['jpg', 'gif', 'jpeg', 'bmp', 'png'],  # 后缀名
                'max_file_size': 10  # 以M为单位
                'min_image_size': (950, 280)    # 以像素为单位
            },
            'origin': {
                'dir': os.path.join('/your/media/root', 'origin'),
                'quality': 100    # 保存质量，可选参数
            },
            'dimensions': {
                'thumb': {
                    'action': 'crop',  # 处理类型，crop表示剪裁
                    'size': (256, 256),
                    'dir': os.path.join('/your/media/root', 'thumb'),
                    'quality': 100    # 保存质量，可选参数
                },
                'normal': {
                    'action': 'scale',  # 处理类型，scale表示缩放
                    'size': (950, 0),  # 缩放操作中，只需指定一边，另一边留0即可
                    'dir': os.path.join('/your/media/root', 'normal'),
                    'quality': 100    # 保存质量，可选参数
                },
            }
        }

    err_code定义：
        11 - 未传入有效的文件
        12 - 图片载入错误
        21 - 文件类型未通过
        22 - 文件过大
        23 - 文件尺寸过小
        41 - 配置错误
        51 - 存储错误
    """

    def __init__(self, config, from_buffer=None, from_file=None):
        self.tfile = from_buffer or from_file
        self.handle_by = 'buffer' if from_buffer else from_file
        self.config = config
        self.error = ''
        self.err_code = 0

    def is_valid(self):
        """
        验证待处理的图片是否符合要求
        """

        if not self.tfile:
            self.err_code, self.error = 11, u'No file supplied.'
            return False

        if self.handle_by == 'buffer':
            # 如果来自上传，则校验有效性
            for name, limit in self.config.get('limits', {}).iteritems():
                func = getattr(self, 'check_' + name, None)
                if func and not func(limit):
                    return False

        # 载入图片
        return self._load()

    def _load(self):
        handler = ImageIOTools.parse if self.handle_by == 'buffer' else ImageIOTools.open

        # 获取文件名
        self.filename = self.tfile.name if self.handle_by == 'buffer' else os.path.basename(self.tfile)

        status, data = handler(self.tfile)
        if status:
            self.image = data
            return True

        self.err_code, self.error = 12, data
        return False

    def _check_formats(self, formats):
        """
        验证上传的图片格式是否符合要求，暂时仅针对后缀进行验证
        """

        ext = os.path.splitext(self.tfile.name)[1].lower().lstrip('.')
        if ext not in formats:
            self.err_code, self.error = 21, 'This type of file is not allowed.'
            return False
        return True

    def _check_max_file_size(self, max_image_size):
        """
        验证上传的图片是否超过文件大小限制
        """

        if self.tfile.size > max_image_size * 1024 * 1024:
            self.err_code, self.error = 22, 'The file is too large. Make sure that the file is less than {0}M.'.format(max_image_size)
            return False
        return True

    def _check_min_image_size(self, limit):
        """
        验证上传的图片尺寸是否小于最小限制
        """

        w, h = get_image_dimensions(self.tfile)
        if w < limit[0] or h < limit[1]:
            self.err_code, self.error = 23, 'The pixel of this image is too small. {0} pixels of width and {1} pixels of height or larger is needed.'.format(*limit)
            return False

    def _save_dimensions(self, format=None):
        dims = self.config.get('dimensions')
        if not type(dims) == dict:
            self.err_code, self.error = 41, 'Config error for dimensions.'
            return False

        for dim in dims.values():
            if not type(dim) == dict:
                continue

            try:
                width, height = dim['size']
                action = dim['action']
                tdir = dim['dir']
                quality = dim['quality']
            except:
                self.err_code, self.error = 41, 'Config error for dimensions.'
                return False

            if action == 'crop':
                # 按所需大小剪裁
                manipulated = ImageTrimTools.auto_crop(self.image, width, height)
            elif action == 'scale':
                # 缩放图片并保持原比例
                manipulated = ImageTrimTools.scale(self.image, width, height)
            else:
                continue

            if not manipulated:
                continue

            result = ImageIOTools.save(manipulated, tdir, self.filename, format, quality)
            if result:
                self.err_code, self.error = 51, result
                return False

        return True

    def _save_origin(self, format=None):
        origin = self.config.get('origin')
        if not origin or not type(origin) == dict or not origin.get('dir'):
            self.err_code, self.error = 41, 'Config error for origin.'
            return False

        result = ImageIOTools.save(self.image, origin.get('dir'), self.filename, format, quality=origin.get('quality', 100))
        if result:
            self.err_code, self.error = 51, result
            return False

        return True

    def save(self, filename='', format=None, save_origin=True):
        """
        保存各尺寸图片，接收三个可选参数：
            filename：要保存的文件名，默认为原文件名；
            format：保存的格式，默认为原格式；
            save_origin：布尔值，指定是否保存原图，默认为True。
        """

        self.filename = filename if filename else self.filename

        if self.handle_by == 'buffer' and save_origin:
            # 此情况下可选择保存原图
            if not self._save_origin(format):
                return False
        if not self._save_dimensions(format):
            return False

        return True
