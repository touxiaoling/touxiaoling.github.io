---
title: 编译并使用openwrt软路由
tags:
---
## 前言
每天网上冲浪,那肯定是要有一个好点的路由器,最普通的作用就是 透明代理,其他还有像 qos,frpc,ddns 和网络相关的服务也可以放在软路由上.
这里还是比较不推荐放在nas上,或者all in one 里.因为路由 是个非常基础的网络部件,就算是家用对稳定性的要求也是比较高的.
而nas,除了数据存储家用还会跑一些折腾的docker服务.说不定哪次就折腾挂了,这时候如果软路由,

## 编译openwrt
如果要自定义feeds建议不要直接修改default,这样之后过几天想再次从最新的代码编译,然后使用‘git pull’的时候,因为你已经修改了文件污染了git工作区,就没办法pull了.而是把feed.conf.default 文件复制一份为 feeds.conf. 这个文件会被git忽略,修改就没有问题了.命令如下:
‘cp feeds.conf.default feeds.conf’ 
openwrt 并不推荐使用 root 编译,但如果执意进行的话,添加环境变量'export FORCE_UNSAFE_CONFIGURE=1'

## 配置openwrt虚拟机

## 一些问题

### lxc

### ipv6

