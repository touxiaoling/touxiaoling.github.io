---
title: Android系统adb设置proxy
tags:
  - Android
  - Proxy
  - adb
abbrlink: b30c046b
date: 2024-01-19 20:25:44
---

## 前言

最近有需求要对 android 进行代理，下面是使用后的一些总结。

对 android 使用 adb 命令设置代理,先使用`adb shell`命令进入 adb shell

然后键入 adb 命令如下

```shell
settings put global http_proxy ${proxy_ip}:${proxy_port}
```

其中`${proxy_ip}`和`${proxy_port}`分别是你要代理的 ip 和端口号。

这条命令使用后，代理是即时生效的。

同时如果你输入下面的命令

```shell
settings list global | grep proxy
```

会发现 `global_http_proxy_host` 和 `global_http_proxy_port`也被自动配上了。

<!--more-->

## 取消代理

如果你需要取消代理，使用如下命令

```shell
settings put global http_proxy :0
```

会立即生效

反之，如果你使用

```shell
settings put global http_proxy ‘’
```

是不会立即生效的，需要重启手机，才能取消代理。

## 设置代理账号和密码

如果你的代理需要配置账号和密码

你可以会照着网上的一些命令

像下面这样配置

```shell
settings put global http_proxy ${proxy_ip}:${proxy_port}
settings put global global_http_proxy_host ${proxy_ip}
settings put global global_http_proxy_port ${proxy_port}
settings put global global_http_proxy_username ${proxy_username}
settings put global global_http_proxy_password ${proxy_password}
```

其中`${proxy_username}`和`${proxy_passwod}`分别是代理的账号和密码

配完之后你会发现没有生效

重启之后也没有生效，并且重启后如果你输入`settings list global | grep proxy`查询代理配置

会发现`global_http_proxy_username`和`global_http_proxy_password`这两项都变成空了

这是因为设备启动时会先查询`http_proxy`的配置，如果存在值，就将值赋值给`global_http_proxy_`各项，所以，想要账密生效，就不要配置`http_proxy`

配置命令如下

```shell
settings put global http_proxy ''
settings put global global_http_proxy_host ${proxy_ip}
settings put global global_http_proxy_port ${proxy_port}
settings put global global_http_proxy_username ${proxy_username}
settings put global global_http_proxy_password ${proxy_password}
```

配置完成后，不会立即生效，需要重启手机。

## 设置排除列表

如果你是使用`global_http_proxy_`各项设置的代理，并且没有配置`http_proxy`

那么还可以实现指定域名列表不做代理的功能，实现方式就是在上文命令的基础上加上

```shell
settings put global global_http_proxy_exclusion_list ${url1},${url2}
```

这里的`${url1}`和`${url2}`是你不想代理的域名，如果有更多可以继续往后添加

注意域名逗号中间不要有空格

## 设置 pac 智能代理

哈哈，没想到吧，系统代理也支持 pac 功能，使用命令如下

```shell
settings put global globa_proxy_pac_url ${pac_url}
```

这里的`${pac_url}`是 pac 文件放置的域名，写法比较复杂，我用的也少，就不细说了。
