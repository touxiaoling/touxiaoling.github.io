---
title: pHash 算法探究
abbrlink: 51c06f9f
date: 2025-06-30 18:18:04
tags:
---


## 1. 算法简介与原理

pHash（感知哈希算法，Perceptual Hash Algorithm）是一种基于图像感知特征的哈希算法。它能够将图像转换为固定长度的哈希值，即使图像经过有损压缩、缩放、亮度调整等变换，生成的哈希值仍然保持相似性，从而实现对相似图像的快速识别与匹配。

该算法的原始思路可参考 [Looks-Like-It](https://hackerfactor.com/blog/index.php%3F/archives/432-Looks-Like-It.html)。

<!--more-->

pHash 算法的基本流程如下：

1. 将图像转换为灰度图，并缩放到固定尺寸（通常为 32×32 像素）；
2. 应用二维离散余弦变换（DCT），提取低频特征（通常为左上角的 8×8 区域）；
3. 计算 DCT 系数的平均值或中位数；
4. 将 DCT 系数与该值比较，生成二进制哈希值。

但在实际实现中，存在一些细节差异，导致不同实现生成的哈希值可能不同，区分度也会有所影响。主要差异包括：

1. 图像缩放的处理方式；
2. 采用平均值还是中位数作为阈值；
3. 8×8 DCT 系数的排列顺序；
4. 比较时是"大于"还是"大于等于"。

## 2. 主流实现分析（C++ pHash）

我查阅了一些参考实现，例如 [pHash 官方网站](https://www.phash.org/)，其代码位于 [aetilius/pHash](https://github.com/aetilius/pHash)（截至目前有 595 个 star，许多语言的 pHash 实现都直接调用该库）。我们可以分析其 `src/pHash.cpp` 部分的核心代码：

```cpp
static const CImg<float> dct_matrix = ph_dct_matrix(32);
int ph_dct_imagehash(const char *file, ulong64 &hash) {
    if (!file) {
        return -1;
    }
    CImg<uint8_t> src;
    try {
        src.load(file);
    } catch (CImgIOException &ex) {
        return -1;
    }
    CImg<float> meanfilter(7, 7, 1, 1, 1);
    CImg<float> img;
    if (src.spectrum() == 3) {
        img = src.RGBtoYCbCr().channel(0).get_convolve(meanfilter);
    } else if (src.spectrum() == 4) {
        int width = src.width();
        int height = src.height();
        img = src.crop(0, 0, 0, 0, width - 1, height - 1, 0, 2)
                  .RGBtoYCbCr()
                  .channel(0)
                  .get_convolve(meanfilter);
    } else {
        img = src.channel(0).get_convolve(meanfilter);
    }

    img.resize(32, 32);
    const CImg<float> &C = dct_matrix;
    CImg<float> Ctransp = C.get_transpose();

    CImg<float> dctImage = (C)*img * Ctransp;

    CImg<float> subsec = dctImage.crop(1, 1, 8, 8).unroll('x');

    float median = subsec.median();
    hash = 0;
    for (int i = 0; i < 64; i++, hash <<= 1) {
        float current = subsec(i);
        if (current > median) hash |= 0x01;
    }

    return 0;
}
```

**步骤说明：**
1. 加载图片后，先将其转换为灰度图像。对于 RGB 图像，先转为 YCbCr 格式，再取亮度通道（channel 0）；
2. 对图像进行均值滤波（mean filter），这一步在很多博客中未提及；
3. 将图像缩放至 32×32，进行 DCT 变换；
4. 取 DCT 结果中第 1～8 行和第 1～8 列（注意 C++ 下标从 0 开始，这里是从第 2 行/列开始），即去除了直流分量（DC）及水平、垂直低频分量；
5. 将 8×8 区域按行优先（row-major）展开为 64 个系数；
6. 计算这 64 个系数的中位数；
7. 依次与中位数比较，大于中位数为 1，小于等于为 0，得到 64 位哈希值。

几点补充说明：

- 第 2 步的均值滤波是为了在缩放前去除高频分量，避免 LANCZOS 等缩放算法对高频过于敏感，这是常见的图像预处理方法；
- 第 4 步从第 1～8 行/列取值，忽略了直流分量和部分低频分量，这样做的合理性值得商榷；
- 使用中位数作为阈值，可以保证哈希值的熵最大（理论上 0 和 1 各占一半）；
- 展开顺序为按行优先（row-major）。


## 3. 主流实现的不足与改进思路

在查阅和分析主流实现的基础上，我有如下思考和优化建议：

1. **图像预处理**：在缩放前先对图像进行一次 3×3 的高斯滤波（或均值滤波），是因为如 Image.Resampling.LANCZOS 这类缩放算法对高频分量较为敏感。滤波有助于去除高频噪声，使缩放后的图像特征更稳定，这是常见的图像处理手段。
2. **DCT 系数选取**：有的实现（如 pHash C++ 版）取 DCT 结果的第 1～8 行/列（即从下标 1 开始），这样不仅去除了直流分量（DC），还去除了水平和垂直的低频分量。虽然去除直流分量有助于消除亮度影响，但进一步去除低频分量是否合理值得商榷。通过逆 DCT（IDCT）实验可以发现，只有第一行或第一列有值时，图像结构差异很大，但如果都去除，这些图像的 pHash 结果会完全相同，区分度反而下降。
3. **阈值选取**：采用中位数作为阈值，可以保证哈希值的熵最大（理论上 0 和 1 各占一半），提升区分能力。若采用平均值，通常会去掉直流分量后再计算平均值。
4. **系数排列顺序**：主流实现多采用按行优先（row-major）展开 8×8 区域。但我认为采用 Zigzag 顺序，即频域能量分布排列会更好（如 JPEG 压缩中的做法）。思路来源：[Not All Bits Are Created Equal](https://nekkidphpprogrammer.
blogspot.com/2014/01/not-all-bits-are-created-equal.html)

**我的优化思路：**
- DCT 系数区域回归为第 0～7 行/列（包含直流分量）；
- 8×8 DCT 系数采用 Zigzag 顺序排列；
- 其他细节与主流实现保持一致。


---

## 4. Python 优化实现

### Zigzag 顺序说明
Zigzag 顺序常用于 JPEG 压缩，能更好地反映频域能量分布。排列如下：

```python
zigzag_8x8 = (
    np.asarray([
        [0, 1, 5, 6, 14, 15, 27, 28],
        [2, 4, 7, 13, 16, 26, 29, 42],
        [3, 8, 12, 17, 25, 30, 41, 43],
        [9, 11, 18, 24, 31, 40, 44, 53],
        [10, 19, 23, 32, 39, 45, 52, 54],
        [20, 22, 33, 38, 46, 51, 55, 60],
        [21, 34, 37, 47, 50, 56, 59, 61],
        [35, 36, 48, 49, 57, 58, 62, 63],
    ]).flatten().argsort()
)
```

### Python 实现

```python
from PIL import Image, ImageFilter
import numpy as np
import scipy.fft

def phash_zigzag(image: Image.Image, hash_size=8, img_size=32):
    # 转为灰度图，滤波后缩放到指定尺寸
    image = image.convert("L").filter(ImageFilter.BoxBlur(3)).resize((img_size, img_size), Image.Resampling.LANCZOS)
    # 计算 DCT，取左上角 8×8 区域，按 zigzag 顺序排列
    dct_low_freq = scipy.fft.dctn(np.asarray(image), norm="ortho", overwrite_x=True)[:hash_size, :hash_size].ravel()[zigzag_8x8]
    # 以中位数为阈值生成哈希
    hash_value = np.packbits(dct_low_freq > np.median(dct_low_freq)).view(np.uint64)[0]
    return hash_value
```

---

## 5. 总结

pHash 算法通过 DCT 提取图像低频特征，主流实现存在一些细节差异。通过分析主流实现的不足，我采用了包含直流分量、zigzag 顺序排列等优化方式,希望本文对理解和改进感知哈希算法有所帮助。



