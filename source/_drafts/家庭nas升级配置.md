---
title: 家庭nas配置升级
tags:
- TrueNAS SCALE
- 万兆网络
---
距离组好nas过去也有三年左右了，硬件一直挺稳定的，
但是升级有四个原因：
一是Truenas系统这三年发生了很大变化，比如arc优化，容器从k3s切换到docker compose，smb共享也有了很多优化。 
二是用的过程中因为初期设定不合理（使用五盘raid5以及3盘raid0），以及折腾了一些特性（没错，说的就是去重，这个用了之后会导致碎片化特别严重，读写速度大幅度降低，而且去重还会占用很多内存！），导致使用的时候有些尴尬。 
三就是相对于三年前，现在万兆内网搭建的价格降低了很多。没错，说的就是 水星SE106 pro，126块钱两个万兆光口，4个2.5g电口,这个价格，让我们可以用400多块钱将nas和pc之间的网络变成万兆。
第四个原因就是折腾永无止境！
所以刚好有时间，就对nas的软件和硬件都进行一次大升级。
<!--more-->

介绍一下原来的配置
机箱 是 8 盘位的万由机箱
cpu 是 intel 10600T
内存 是 2666MHz DDR4 162+82
主板 是 技嘉小雕 (B460M AORUS PRO) 主板.
因为主板上只有 6 口 SATA, 所以又加了一块 SATA3.0 4 口拓展卡凑出来 8 口.
电源 是 买机箱的时候送的益衡 300W 模块