# Copyright (c) OpenMMLab. All rights reserved.
import os.path as osp

import mmcv
import numpy as np
import cv2

from ..builder import PIPELINES

def load_ENVI_hyperspectral_image_from_file(filename):
    ENVI_data_type = [None,
                      np.uint8,     # 1
                      np.int16,     # 2
                      np.int32,     # 3
                      np.float32,   # 4
                      np.float64,   # 5
                      None,
                      None,
                      None,
                      None,
                      None,
                      None,
                      np.uint16,    # 12
                      np.uint32,]   # 13
    hdr = dict()
    with open(filename) as f:
        for line in f.readlines():
            if '=' not in line:
                continue
            else:
                key, value = line.split('=')
                key = key.strip()
                value = value.strip()
                hdr[key] = value
    # assert hdr['file type'] == 'ENVI Standard', \
    #     'Require ENVI data: file type = ENVI Standard'
    # assert hdr['byte order'] == '0', \
    #     'Require ENVI data: byte order = 0'
    # assert hdr['x start'] == '0', \
    #     'Require ENVI data: x start = 0'
    # assert hdr['y start'] == '0', \
    #     'Require ENVI data: y start = 0'
    assert int(hdr['data type']) <= len(ENVI_data_type) and ENVI_data_type[int(hdr['data type'])] != None, \
        'Unrecognized data type'

    data_type = int(hdr['data type'])
    header_offset = int(hdr['header offset'])
    height = int(hdr['lines'])
    width = int(hdr['samples'])
    bands = int(hdr['bands'])
    img_bytes = np.fromfile(filename.replace('.hdr', '.raw'), dtype=ENVI_data_type[data_type],
                            offset=header_offset)
    if hdr['interleave'].lower() == 'bsq':
        img_bytes = img_bytes.reshape((bands, height, width))
        img_bytes = np.transpose(img_bytes, (1, 2, 0))
    elif hdr['interleave'].lower() == 'bip':
        img_bytes = img_bytes.reshape((height, width, bands))
    elif hdr['interleave'].lower() == 'bil':
        img_bytes = img_bytes.reshape((height, bands, width))
        img_bytes = np.transpose(img_bytes, (0, 2, 1))
    else:
        raise ValueError('Unrecognized interleave, for more information please email:1395133179@qq.com')
    return img_bytes


@PIPELINES.register_module()
class LoadENVIHyperSpectralImageFromFile(object):
    """Load an ENVI Hyper Spectral Image from file.
    TODO: rewrite the helping document
    Required keys are "img_prefix" and "img_info" (a dict that must contain the
    key "filename"). Added or updated keys are "filename", "img", "img_shape",
    "ori_shape" (same as `img_shape`), "pad_shape" (same as `img_shape`),
    "scale_factor" (1.0) and "img_norm_cfg" (means=0 and stds=1).

    Args:
        to_float32 (bool): Whether to convert the loaded image to a float32
            numpy array. If set to False, the loaded image is an uint8 array.
            Defaults to False.
        color_type (str): The flag argument for :func:`mmcv.imfrombytes`.
            Defaults to 'color'.
        file_client_args (dict): Arguments to instantiate a FileClient.
            See :class:`mmcv.fileio.FileClient` for details.
            Defaults to ``dict(backend='disk')``.
        imdecode_backend (str): Backend for :func:`mmcv.imdecode`. Default:
            'cv2'
    """

    def __init__(self,
                 channel_select,
                 to_float32=True,
                 normalization=True,
                 channel_to_show=(10, 20, 30),
                 median_blur=True):
        self.to_float32 = to_float32
        self.normalization = normalization
        self.channel_select = channel_select
        self.channel_to_show = channel_to_show
        self.median_blur = median_blur


    def __call__(self, results):
        """Call functions to load image and get image meta information.

        Args:
            results (dict): Result dict from :obj:`mmseg.CustomDataset`.

        Returns:
            dict: The dict contains loaded image and meta information.
        """

        if results.get('img_prefix') is not None:
            filename = osp.join(results['img_prefix'],
                                results['img_info']['filename'])
        else:
            filename = results['img_info']['filename']

        img_bytes = load_ENVI_hyperspectral_image_from_file(filename)

        img_bytes = img_bytes[:, :, self.channel_select]
        if self.to_float32:
            img_bytes = img_bytes.astype(np.float32)
            if self.normalization:
                img_bytes -= np.mean(img_bytes,axis=(0,1),keepdims=True)
                img_bytes /= np.clip(np.std(img_bytes,axis=(0,1),keepdims=True), 1e-6, 1e6)
                # img_bytes -= np.min(img_bytes)
                # img_bytes /= np.max(img_bytes)
        if self.median_blur:
            for band in range(img_bytes.shape[0]):
                img_bytes[band, :, :] = cv2.medianBlur(img_bytes[band, :, :], ksize=3)

        results['filename'] = filename.replace('.hdr', '.png')
        results['ori_filename'] = results['img_info']['filename'].replace('.hdr', '.png')
        results['img'] = img_bytes
        results['img_shape'] = img_bytes.shape
        results['ori_shape'] = img_bytes.shape
        # Set initial values for default meta_keys
        results['pad_shape'] = img_bytes.shape
        results['scale_factor'] = 1.0
        results['channel_select'] = self.channel_select
        results['channel_to_show'] = self.channel_to_show
        num_channels = 1 if len(img_bytes.shape) < 3 else img_bytes.shape[2]
        mean = np.ones(num_channels, dtype=np.float32)*128
        std = np.ones(num_channels, dtype=np.float32)*16
        results['img_norm_cfg'] = dict(
            mean=mean,
            std=std,
            to_rgb=False)
        return results

    def __repr__(self):
        repr_str = self.__class__.__name__
        repr_str += f'(channel_select={self.channel_select},'
        repr_str += f'to_float32={self.to_float32},'
        repr_str += f'normalization={self.normalization},'
        repr_str += f'channel_to_show={self.channel_to_show},'
        repr_str += f'median_blur={self.median_blur})'
        return repr_str

@PIPELINES.register_module()
class LoadENVIHyperSpectralImageFromFileAndPCA(object):
    """Load an ENVI Hyper Spectral Image from file.
    TODO: rewrite the helping document
    Required keys are "img_prefix" and "img_info" (a dict that must contain the
    key "filename"). Added or updated keys are "filename", "img", "img_shape",
    "ori_shape" (same as `img_shape`), "pad_shape" (same as `img_shape`),
    "scale_factor" (1.0) and "img_norm_cfg" (means=0 and stds=1).

    Args:
        to_float32 (bool): Whether to convert the loaded image to a float32
            numpy array. If set to False, the loaded image is an uint8 array.
            Defaults to False.
        color_type (str): The flag argument for :func:`mmcv.imfrombytes`.
            Defaults to 'color'.
        file_client_args (dict): Arguments to instantiate a FileClient.
            See :class:`mmcv.fileio.FileClient` for details.
            Defaults to ``dict(backend='disk')``.
        imdecode_backend (str): Backend for :func:`mmcv.imdecode`. Default:
            'cv2'
    """

    def __init__(self,
                 channel_keep,
                 to_float32=True,
                 normalization=True,
                 channel_to_show=(10, 20, 30),
                 median_blur=True):
        self.to_float32 = to_float32
        self.normalization = normalization
        self.channel_keep = channel_keep
        self.channel_to_show = channel_to_show
        self.median_blur = median_blur

        self.mean_vector = np.load('./data/HSI/mean_vector.npy')
        self.std_vector = np.load('./data/HSI/std_vector.npy')
        self.pca_vector = np.load('./data/HSI/pca_vector.npy')[:, :channel_keep]

    def __call__(self, results):
        """Call functions to load image and get image meta information.

        Args:
            results (dict): Result dict from :obj:`mmseg.CustomDataset`.

        Returns:
            dict: The dict contains loaded image and meta information.
        """

        if results.get('img_prefix') is not None:
            filename = osp.join(results['img_prefix'],
                                results['img_info']['filename'])
        else:
            filename = results['img_info']['filename']

        img_bytes = load_ENVI_hyperspectral_image_from_file(filename)
        height, width, bands = img_bytes.shape

        img_bytes = img_bytes.reshape((-1, bands)).astype(np.float32)
        img_bytes -= self.mean_vector
        img_bytes /= self.std_vector
        img_bytes = np.dot(img_bytes, self.pca_vector)
        img_bytes = img_bytes.reshape((height, width, -1))

        if self.to_float32:
            img_bytes = img_bytes.astype(np.float32)
            if self.normalization:
                img_bytes -= np.mean(img_bytes,axis=(0,1),keepdims=True)
                img_bytes /= np.clip(np.std(img_bytes,axis=(0,1),keepdims=True), 1e-6, 1e6)
                # img_bytes -= np.min(img_bytes)
                # img_bytes /= np.max(img_bytes)
        if self.median_blur:
            for band in range(img_bytes.shape[0]):
                img_bytes[band, :, :] = cv2.medianBlur(img_bytes[band, :, :], ksize=3)

        results['filename'] = filename.replace('.hdr', '.png')
        results['ori_filename'] = results['img_info']['filename'].replace('.hdr', '.png')
        results['img'] = img_bytes
        results['img_shape'] = img_bytes.shape
        results['ori_shape'] = img_bytes.shape
        # Set initial values for default meta_keys
        results['pad_shape'] = img_bytes.shape
        results['scale_factor'] = 1.0
        results['channel_select'] = self.channel_keep
        results['channel_to_show'] = self.channel_to_show
        num_channels = 1 if len(img_bytes.shape) < 3 else img_bytes.shape[2]
        mean = np.ones(num_channels, dtype=np.float32)*128
        std = np.ones(num_channels, dtype=np.float32)*16
        results['img_norm_cfg'] = dict(
            mean=mean,
            std=std,
            to_rgb=False)
        return results

    def __repr__(self):
        repr_str = self.__class__.__name__
        repr_str += f'(channel_keep={self.channel_keep},'
        repr_str += f'to_float32={self.to_float32},'
        repr_str += f'normalization={self.normalization},'
        repr_str += f'channel_to_show={self.channel_to_show},'
        repr_str += f'median_blur={self.median_blur})'
        return repr_str


@PIPELINES.register_module()
class LoadENVIHyperSpectralImageFromFileWithExtra(object):
    """Load an ENVI Hyper Spectral Image from file.
    TODO: rewrite the helping document
    Required keys are "img_prefix" and "img_info" (a dict that must contain the
    key "filename"). Added or updated keys are "filename", "img", "img_shape",
    "ori_shape" (same as `img_shape`), "pad_shape" (same as `img_shape`),
    "scale_factor" (1.0) and "img_norm_cfg" (means=0 and stds=1).

    Args:
        to_float32 (bool): Whether to convert the loaded image to a float32
            numpy array. If set to False, the loaded image is an uint8 array.
            Defaults to False.
        color_type (str): The flag argument for :func:`mmcv.imfrombytes`.
            Defaults to 'color'.
        file_client_args (dict): Arguments to instantiate a FileClient.
            See :class:`mmcv.fileio.FileClient` for details.
            Defaults to ``dict(backend='disk')``.
        imdecode_backend (str): Backend for :func:`mmcv.imdecode`. Default:
            'cv2'
    """

    def __init__(self,
                 channel_select,
                 to_float32=True,
                 normalization=True,
                 channel_to_show=(10, 20, 30),
                 median_blur=True,
                 label_smoothing=5):
        self.to_float32 = to_float32
        self.normalization = normalization
        self.channel_select = channel_select
        self.channel_to_show = channel_to_show
        self.median_blur = median_blur
        self.label_smoothing = (label_smoothing, label_smoothing)


    def __call__(self, results):
        """Call functions to load image and get image meta information.

        Args:
            results (dict): Result dict from :obj:`mmseg.CustomDataset`.

        Returns:
            dict: The dict contains loaded image and meta information.
        """
        if 'filename' in results['img_info'].keys():
            if results.get('img_prefix') is not None:
                filename = osp.join(results['img_prefix'],
                                    results['img_info']['filename'])
            else:
                filename = results['img_info']['filename']

            img_bytes = load_ENVI_hyperspectral_image_from_file(filename)
        else:
            if results.get('full_positive_prefix') is not None:
                positive = osp.join(results['full_positive_prefix'],
                                    results['img_info']['positive']['filename'])
            else:
                positive = results['img_info']['positive']
            img_bytes_positive = load_ENVI_hyperspectral_image_from_file(positive)
            if self.to_float32:
                img_bytes_positive = img_bytes_positive.astype(np.float32)
                if self.normalization:
                    img_bytes_positive -= np.mean(img_bytes_positive,axis=(0,1),keepdims=True)
                    img_bytes_positive /= np.clip(np.std(img_bytes_positive,axis=(0,1),keepdims=True), 1e-6, 1e6)
            if results.get('full_negative_prefix') is not None:
                negative = osp.join(results['full_negative_prefix'],
                                    results['img_info']['negative']['filename'])
            else:
                negative = results['img_info']['negative']
            img_bytes_negative = load_ENVI_hyperspectral_image_from_file(negative)
            if self.to_float32:
                img_bytes_negative = img_bytes_negative.astype(np.float32)
                if self.normalization:
                    img_bytes_negative -= np.mean(img_bytes_negative,axis=(0,1),keepdims=True)
                    img_bytes_negative /= np.clip(np.std(img_bytes_negative,axis=(0,1),keepdims=True), 1e-6, 1e6)
            if results.get('seg_prefix', None) is not None:
                ann = osp.join(results['seg_prefix'],
                               results['ann_info']['seg_map'])
            else:
                ann = results['ann_info']['seg_map']
            ann = cv2.imread(ann, flags=cv2.IMREAD_UNCHANGED) * 255
            ann = cv2.blur(ann, ksize=self.label_smoothing).astype(np.float32) / 255
            ann = np.expand_dims(ann, -1)
            img_bytes = ann * img_bytes_positive + (1 - ann) * img_bytes_negative


        img_bytes = img_bytes[:, :, self.channel_select]
        if self.to_float32:
            img_bytes = img_bytes.astype(np.float32)
            if self.normalization:
                img_bytes -= np.mean(img_bytes,axis=(0,1),keepdims=True)
                img_bytes /= np.clip(np.std(img_bytes,axis=(0,1),keepdims=True), 1e-6, 1e6)
                # img_bytes -= np.min(img_bytes)
                # img_bytes /= np.max(img_bytes)
        if self.median_blur:
            for band in range(img_bytes.shape[0]):
                img_bytes[band, :, :] = cv2.medianBlur(img_bytes[band, :, :], ksize=3)

        if 'filename' in results['img_info'].keys():
            results['filename'] = filename.replace('.hdr', '.png')
            results['ori_filename'] = results['img_info']['filename'].replace('.hdr', '.png')
        else:
            results['filename'] = results['ann_info']['seg_map'].replace('.hdr', '.png')
            results['ori_filename'] = results['ann_info']['seg_map'].replace('.hdr', '.png')
        results['img'] = img_bytes
        results['img_shape'] = img_bytes.shape
        results['ori_shape'] = img_bytes.shape
        # Set initial values for default meta_keys
        results['pad_shape'] = img_bytes.shape
        results['scale_factor'] = 1.0
        results['channel_select'] = self.channel_select
        results['channel_to_show'] = self.channel_to_show
        num_channels = 1 if len(img_bytes.shape) < 3 else img_bytes.shape[2]
        mean = np.ones(num_channels, dtype=np.float32)*128
        std = np.ones(num_channels, dtype=np.float32)*16
        results['img_norm_cfg'] = dict(
            mean=mean,
            std=std,
            to_rgb=False)
        return results

    def __repr__(self):
        repr_str = self.__class__.__name__
        repr_str += f'(channel_select={self.channel_select},'
        repr_str += f'to_float32={self.to_float32},'
        repr_str += f'normalization={self.normalization},'
        repr_str += f'channel_to_show={self.channel_to_show},'
        repr_str += f'median_blur={self.median_blur},'
        repr_str += f'label_smoothing={self.label_smoothing})'
        return repr_str



'''
cv2.imwrite('ann.png', (ann*255).astype(np.uint8))
for i in range(60):
    cv2.imwrite(f'{i}.png', (img_bytes[:,:,i]*8+128).astype(np.uint8))
for i in range(60):
    cv2.imwrite(f'{i}+.png', (img_bytes_positive[:,:,i]*8+128).astype(np.uint8))
for i in range(60):
    cv2.imwrite(f'{i}-.png', (img_bytes_negative[:,:,i]*8+128).astype(np.uint8))
'''
