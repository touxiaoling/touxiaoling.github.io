---
title: 在群晖中使用docker搭建TTRSS+RSSHub并启用https
tags:
- TTRSS
- docker
- RSSHub
- Nginx
- frp
- https
- 群晖
- watchtower
abbrlink: '37149971'
date: 2022-05-13 17:45:54
---

## 前言
目前个人获取信息的方式十分的平台化,而每个平台基本上又都是以使用时间为条件给你推荐各种东西,比如奶子啊奶子啊还有奶子啊什么的,搞得我身体很不好.  
开玩笑,rss可以让我们主动从各个平台获取信息而不被绑架自己的视野,这非常有用.比如b站不会给你推荐抖音上的东西,抖音也不会给你推荐其他平台上的东西,其他平台还有v2ex,知乎,微博,大家因为常用平台不一样看到的东西也非常的不一样.  
但是跨平台的浏览不得不说又十分的麻烦.还有就是不同平台的排行榜都是处于自己利益定制的,另外还有一些不能在国内轻易访问的网站(非情色).
还有就是像孤岛一样的半年不更新一次的个人博客,这种就更难主动去访问了,如果想抓取不同平台的热门内容还有你想关注的内容汇总到一起,RSS就是一个非常棒的一站式工具.  
当然,只是收集强时间相关的信息上来说.  
不过很尴尬的是,目前并没有一个可以说特别好用的RSS平台,TTRSS相对来说是比较不错的一个,但用了一阵以后发现启动速度相对来说还是比较慢.嘛,怎么说,只能交给时间解决了.  
<!--more-->

## 前置知识
前置需要了解一些关于docker以及docker-compose的基本知识和基本命令.  
docker在群晖的安装很简单,只要在套件库里面搜索docker然后安装上就可以了.其它系统的安装见官方页:https://docs.docker.com/get-docker/  
我是在自己的黑群晖小机器里搭建的.docker版本是20.10.3,docker-compose 版本是1.28.5,注意docker-compose版本最好大于1.17,不然会有点bug.  

## 搭建ttrsss
新建一个名叫`ttrss`的文件夹,然后在里面新建一个名叫`docker-compose.yml`的文件.
```bash
mkdir ttrss
cd ttrss
touch docker-compose.yml
```
然后在该文件中写入如下内容:
```yaml
services:
  service.rss:
    image: wangqiru/ttrss:latest
    container_name: ttrss
    labels:
      com.centurylinklabs.watchtower.enable: true
    environment:
      SELF_URL_PATH: http://机器ip:31480 # please change to your own domain
      DB_PASS: ttrss # use the same password defined in `database.postgres`
      PUID: 1026
      PGID: 100
    ports:
      - 31480:80
    volumes:
      - feed-icons:/var/www/feed-icons/
    networks:
      - public_access
      - service_only
      - database_only
    stdin_open: true
    tty: true
    depends_on:
        - service.mercury
        - service.opencc
        - database.postgres
    restart: always

  service.mercury: # set Mercury Parser API endpoint to `service.mercury:3000` on TTRSS plugin setting page
    image: wangqiru/mercury-parser-api:latest
    labels:
      com.centurylinklabs.watchtower.enable: true
    networks:
      - public_access
      - service_only
    restart: always

  service.opencc: # set OpenCC API endpoint to `service.opencc:3000` on TTRSS plugin setting page
    image: wangqiru/opencc-api-server:latest
    labels:
      com.centurylinklabs.watchtower.enable: true
    environment:
      NODE_ENV: production
    networks:
      - service_only
    restart: always

  database.postgres:
    image: postgres:13-alpine
    labels:
      com.centurylinklabs.watchtower.enable: true
    environment:
      - POSTGRES_PASSWORD=ttrss # feel free to change the password
    volumes:
      - postgres-data:/var/lib/postgresql/data # persist postgres data to ~/postgres/data/ on the host
    networks:
      - database_only
    restart: always
volumes:
  feed-icons:
  postgres-data:

networks:
  public_access: # Provide the access for ttrss UI
  service_only: # Provide the communication network between services only
    internal: true
  database_only: # Provide the communication between ttrss and database only
    internal: true

```
注意,SELF_URL_PATH 处要填写你启动docker机器的ip,PUID和PGID是docker容器的用户id和组id,这个如果填错了好像也不会怎么样,只要你是用的创建的虚拟卷.  
在命令行使用`docker-compose up -d`启动docker-compose容器.然后在浏览器中访问 http://机器ip:31480 就可以看到你的ttrss网站了.

## 搭建rsshub
rsshub的官方网站是: https://docs.rsshub.app/ , 可以给各种各样的网站生成rss订阅源.帮助我们实现跨平台订阅的想法.  
你可以直接使用在线的rsshub订阅源来访问一些反爬不是特别严格的网站,但某些反爬严格比如微博某个博主的更新,就最好是自建RSSHub服务了.  
不过搭建也很简单,我们直接在刚才的`docker-compose.yml`文件中增加一些关于rsshub的内容即可.
```yaml
services:
  service.rss:
    image: wangqiru/ttrss:latest
    container_name: ttrss
    labels:
      com.centurylinklabs.watchtower.enable: true
    environment:
      SELF_URL_PATH: http://机器ip:31480 # please change to your own domain
      DB_PASS: ttrss # use the same password defined in `database.postgres`
      PUID: 1026
      PGID: 100
    ports:
      - 31480:80
    volumes:
      - feed-icons:/var/www/feed-icons/
    networks:
      - public_access
      - service_only
      - database_only
    stdin_open: true
    tty: true
    depends_on:
        - rsshub
        - service.mercury
        - service.opencc
        - database.postgres
    restart: always

  service.mercury: # set Mercury Parser API endpoint to `service.mercury:3000` on TTRSS plugin setting page
    image: wangqiru/mercury-parser-api:latest
    labels:
      com.centurylinklabs.watchtower.enable: true
    networks:
      - public_access
      - service_only
    restart: always

  service.opencc: # set OpenCC API endpoint to `service.opencc:3000` on TTRSS plugin setting page
    image: wangqiru/opencc-api-server:latest
    labels:
      com.centurylinklabs.watchtower.enable: true
    environment:
      NODE_ENV: production
    networks:
      - service_only
    restart: always

  rsshub:
    image: diygod/rsshub
    restart: always
    labels:
      com.centurylinklabs.watchtower.enable: true
    environment:
      PORT: 80
      NODE_ENV: production
      CACHE_TYPE: redis
      REDIS_URL: 'redis://database.redis:6379/'
      PUPPETEER_WS_ENDPOINT: 'ws://service.browserless:3000'
    networks:
      - public_access
      - database_only
    depends_on:
        - database.redis
        - service.browserless

  service.browserless:
    image: browserless/chrome
    labels:
      com.centurylinklabs.watchtower.enable: true
    restart: always
    ulimits:
      core:
        hard: 0
        soft: 0

  database.redis:
    image: redis:alpine
    restart: always
    labels:
      com.centurylinklabs.watchtower.enable: true
    volumes:
        - redis-data:/data
    networks:
      - database_only

  database.postgres:
    image: postgres:13-alpine
    labels:
      com.centurylinklabs.watchtower.enable: true
    environment:
      - POSTGRES_PASSWORD=ttrss # feel free to change the password
    volumes:
      - postgres-data:/var/lib/postgresql/data # persist postgres data to ~/postgres/data/ on the host
    networks:
      - database_only
    restart: always

volumes:
  feed-icons:
  redis-data:
  postgres-data:

networks:
  public_access: # Provide the access for ttrss UI
  service_only: # Provide the communication network between services only
    internal: true
  database_only: # Provide the communication between ttrss and database only
    internal: true
```
然后运行`docker-compose up -d`即可.因为都在同一个compose文件,也在同一个`public_access`网络下,所以ttrss可以使用`rsshub`做域名直接解析到rsshub的ip.  
想要在ttrss中订阅rsshub的链接,比如b站番剧就是 http://rsshub/bilibili/bangumi/media/9192
更详细的文档可以看https://docs.rsshub.app/

## 配置watchtower自动更新
如果使用本地的RSSHub服务,有一个小问题是它经常更新...,如果手动来的话会很麻烦,所以我们可以使用watchtower来监控他们进行自动更新.
我们再新建一个叫`watchtower`的文件夹,然后在里面再创建一个`docker-compose.yml`文件
```bash
mkdir rsshub
cd rsshub
touch docker-compose.yml
```
然后在里面写如下内容:

```yaml
version: "3.8"
services:
  watchtower:
    image: containrrr/watchtower:latest
    container_name: watchtower
    restart: always
    environment:
      TZ: Asia/Shanghai
      WATCHTOWER_LABEL_ENABLE: "true"
      WATCHTOWER_CLEANUP: "true"
      WATCHTOWER_SCHEDULE: "0 30 4 * * *"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```
然后运行`docker-compose up -d`即可启动一个wathtower容器,它会在每天4.30检测并更新容器.  
如果不经过一些其他特殊配置,watchtower容器一个宿主机只能运行一个,多个会相互冲突.不过一般来说一个就足够了.  
如果你还有其他docker container 在运行也希望一并检测的话,给对应的容器增加一个`com.centurylinklabs.watchtower.enable: true`的label即可.  

## 启用https访问
ttrss默认是使用http访问的,而现在的chrome浏览器不建议http访问,所以我们可以申请一个https证书,使用nginx将http转成https再访问ttrss.  
如果要启用https,首先我们需要一个个人域名,在国内买的话需要备案,如果不想要备案的话也可以在一些国外的比如godaddy上注册一个域名.价格应该不会特别贵.  
如果实在不想买的话就要考虑一些骚操作,不过我还是建议花钱买省心.有一个个人域名会方便很多.  
### 创建acme.sh容器
下面我就假设你已经有个一个域名,接下来就是神奇一个https证书.
证书的申请可以使用acme.sh,这个是一个自动申请免费证书的工具,还可以检测快到期自动重新申请.
我们再新建一个叫`acme.sh`的文件夹,然后在里面再创建一个`docker-compose.yml`文件和一个名叫`out`的文件夹.
```bash
mkdir acme.sh
cd acme.sh
mkdir out
touch docker-compose.yml
```
然后在里面写如下内容:
```yaml

version: "3.8"
services:
  acme.sh:
    image: neilpang/acme.sh:latest
    container_name: acme.sh
    restart: always
    labels:
      com.centurylinklabs.watchtower.enable: true
    environment:
      GD_Secret: MYSELF_PRIVETE_SECRET
      GD_Key: MYSELF_PRIVETE_KEY
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./out:/acme.sh
    command: daemon
```
因为我是在godaddy上申请的,所以申请证书就需要填入这里的`GD_Secret` 和`GD_Key`两个内容.这两个值可以在godaddy的开发者网站上申请.
网址是: https://这里有一个网址等待补全.com/  
使用`docker-compose up -d`即可启动acme.sh容器,它会在后台检测你已经申请的证书是否到期并续期.  

### 申请https证书
然后注册一个账号  
```bash
sudo docker exec acme.sh --register-account -m youremail@mail.com
```
注意`youremail@mail.com`是填你自己的邮箱地址.  
然后敲下面的命令开始申请证书,注意`yourdomain.com`是填你要申请证书的域名,请确保这个域名你自己是拥有者.
```bash
sudo docker exec acme.sh --issue --dns dns_gd -d yourdomain.com
```
这个命令会申请一个证书,并且把它保存到`/acme.sh/out/yourdomain.com`目录下.不过我们不会直接操作out目录下的内容.也不会去手动copy它,这样他不会自动更新.  
### 创建nginx容器
接下来我们创建一个nginx容器.在ttrss的docker-compose.yml文件中,我们增加一些内容:
```yaml
等待补全
```
### 导入https证书到ngnix

### 在路由器配置DNS域名劫持
在路由器设置域名DNS解析劫持.
## 暴露TTRSS到公网访问
这样我们就可以在本地的局域网愉快的使用ttrss了.不过如果出门怎么办呢,rss非常适合在坐地铁的使用使用不是吗?只能在家用也太不方便了.
所以我们要将tttrss暴露到公网,前一步的启用https也是为了增加暴漏到公网的安全性.  
这一步我们需要有一个固定的公网ip地址,或者DDNS,不过家用ip启动web服务是违法的,如果不备案的话我推荐是购买一个云服务器(国外),以及国外域名,这样会省很多事,不然还是乖乖备案叭.
