---
title: windows wsl2配置ssh server并可以从其他计算机链接
abbrlink: dbc07926
date: 2023-06-01 21:56:03
tags:
---

## 前言 
wsl2是个好东西,但因为网络的问题,wsl2的ip和局域网ip并不在一个层级,如果从其他机器B访问这台机器A的wsl2是不通的.
而且还有个问题就是,wsl2的ip是随机分配的,会不停的变动,在本级可以通过`localhost`来访问,但是其他机器就不能使用了.
我查找的教程都是通过比如说端口转发什么,这个如果wsl2的ip变动了,就要重新配置,比较麻烦.
我想到一个新的方法就是通过跳板机的方式,先ssh进本机,然后再从本机ssh到wsl2
这样的好处就是也不用查询wsl2的ip是多少了,比如你的本机ip是192.168.31.155 用户是 user ,配置好后只需输入`ssh root@localhost -J user@192.168.31.155` 即可从ssh 进wsl2.
接下来讲下配置方式.

## 配置机器A的ssh
### 安装openssh
win10 win11 都支持安装openssh server,可以参考这个链接:https://learn.microsoft.com/zh-cn/windows-server/administration/openssh/openssh_install_firstuse

> 若要安装 OpenSSH 组件：
>
> 打开“设置”，选择“应用”>“应用和功能”，然后选择“可选功能” 。
>
> 扫描列表，查看是否已安装 OpenSSH。 如果未安装，请在页面顶部选择“添加功能”，然后：
>
> 1. 查找“OpenSSH 客户端”，再单击“安装”
> 2. 查找“OpenSSH 服务器”，再单击“安装”
> 设置完成后，回到“应用”>“应用和功能”和“可选功能”，你应会看到已列出 OpenSSH 。

### 配置openssh
这样安装完openssh是不用再设置防火墙的,如果你打开防火墙会发现, windows已经自动配置好了openssh的22端口监听.
不过,sshd服务是默认关闭的,需要 打开 服务 -> openssh 右键 启动. 可以在属性里将这个服务设置为自动启动.
然后我们就可以尝试从其他机器ssh这台windows了.


### 查看机器B公钥
我们将另外一台机器B的公钥添加到机器A上,这样ssh登陆就不用输入密码了.我的机器B是一台mac,在命令行输入`cat ~/.ssh/id_rsa.pub`输出的就是机器B的公钥,复制下来.
如果找不到文件的话,代表你还没有ssh key ,键入 `ssh-keygen` 命令,然后一路回车就可在机器B上创建ssh key,然后重新`cat ~/.ssh/id_rsa.pub`查看公钥.

### 添加机器B的公钥到机器A
在linux下,公钥直接添加到`~/.ssh/authorized_keys`文件下面就好了.
但在windows下面,这里是有一些不一样的,如果你是管理员账户的话(一般家用一个用户都是管理员账户,注意有管理员权限就是管理员账户),那你就要把机器B的公钥添加到`C:\ProgramData\ssh\sshd_config\administrators_authorized_keys`文件下面才行.
注意: 是`ProgramData` 不是`Program File`

### 禁用密码登陆
为了安全起见,我推荐将允许密码登陆给关掉,使用公钥的方式登陆. windows的sshd 的config文件位置是 `C:\ProgramData\ssh\sshd_config`
用记事本或者vscode打开之后找到再最后添加`PasswordAuthentication no`,即可禁用密码登陆.

### 重启openssh
在开始菜单搜索 服务 ,然后找到 openssh 右键停止 然后再右键运行.即可重启openssh.
然后尝试从机器B登陆到机器A试试. 在机器B输入命令`ssh user@192.168.31.155`
注意 user代表你的windows用户名 就是`C:\user`文件夹下面的那个你的用户名文件夹的名字. `192.168.31.155`就是机器A的ip,可以在powershell输入`ipconfig`查看.

### 备注: openssh 调试
如果你配置完之后无法正常从机器B ssh到机器A,那么可以手动将 服务 里的 openssh 关掉. 打开powershell,输入`sshd -d`
然后再从机器B ssh 到机器A,powershell会打印出无法连接的原因.


## 配置机器A的wsl2的ssh

### 重装ssh
输入
```bash
sudo apt remove openssh-server -y
sudo apt install openssh-server -y
```
### 放入公钥
如果不存在 `~/.ssh`文件夹,那输入 `ssh-keygen` 生成ssh key
然后将机器B的公钥放在`~/.ssh/authorized_keys`里面
注意`authorized_keys` 文件的权限,最好用`chmod 600 ~/.ssh/authorized_keys`重设下权限.

### 重启ssh服务
输入下面的命令重启sshd
```bash
systemctl restart ssh
```

## 结束
这样配置好之后就万事大吉啦,尝试使用ssh登陆吧,输入命令
`ssh root@localhost -J user@192.168.31.155`
记得将机器A的ip和用户名替换成自己的.
## 一些其它方法

比如: https://blog.meathill.com/wsl/wsl2-setup-ssh-server-and-connect-from-external-machine.html
这样就不用跳板机直接连入wsl2了,但是就没办法进入本机的powershell了.
