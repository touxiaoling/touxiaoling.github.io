---
title: BitTorrent DHT网络爬虫实现详解
tags: [BitTorrent, DHT, 网络爬虫, Python, 分布式系统]
date: 2024-12-20
---

## 引言

BitTorrent DHT（分布式哈希表）是P2P网络中用于节点发现和资源定位的核心组件。通过构建DHT网络爬虫，我们可以深入了解P2P网络的拓扑结构、节点分布特征以及热门资源传播规律。本文将详细介绍BitTorrent DHT网络爬虫的实现原理和技术细节。

## DHT网络基础

### 什么是DHT

分布式哈希表（Distributed Hash Table, DHT）是一种去中心化的分布式存储系统，它允许节点在无需中心服务器的情况下存储和检索数据。在BitTorrent网络中，DHT主要用于：

1. **节点发现**：帮助客户端找到其他peer节点
2. **资源定位**：通过info_hash查找种子文件
3. **网络维护**：维护路由表和节点状态

### Kademlia协议

BitTorrent DHT基于Kademlia协议，这是一个高效的分布式哈希表实现。Kademlia的核心创新在于使用异或距离度量和并行查找机制。

#### 核心参数

- **k = 8**：每个bucket最多存储8个节点，也是每个键值的复制因子
- **α = 3**：并行查找时同时查询的节点数
- **B = 160**：键和节点ID的位数（SHA-1哈希）

#### 异或距离度量

Kademlia使用异或运算定义节点间的"距离"：

```
distance(x, y) = x XOR y
```

**距离特性**：
- 非负性：`distance(x, y) ≥ 0`
- 同一性：`distance(x, y) = 0` 当且仅当 `x = y`
- 对称性：`distance(x, y) = distance(y, x)`
- 三角不等式：`distance(x, y) + distance(y, z) ≥ distance(x, z)`

**距离计算示例**：
```
节点A: 00101100110100101101 (二进制)
节点B: 10110011011010011011 (二进制)
距离: 10011111101110110101 (二进制) = 0x9F75D (十六进制)
```

#### k-bucket路由表结构

每个节点维护160个bucket，对应ID空间的每一位：

```
Bucket 0:  距离范围 [1, 2)      - 最近节点
Bucket 1:  距离范围 [2, 4)
Bucket 2:  距离范围 [4, 8)
...
Bucket i:  距离范围 [2^i, 2^(i+1))
...
Bucket 159: 距离范围 [2^159, 2^160) - 最远节点
```

**bucket索引计算**：
```python
def get_bucket_index(self, target_id: bytes) -> int:
    """计算目标节点对应的bucket索引"""
    distance = int.from_bytes(self.node_id, 'big') ^ int.from_bytes(target_id, 'big')
    return distance.bit_length() - 1 if distance != 0 else 0
```

#### 迭代查找算法

Kademlia使用高效的迭代查找机制来定位节点和键值：

**FIND_NODE算法**：
```python
async def iterative_find_node(self, target_id: bytes) -> List[Node]:
    """迭代查找指定ID的节点"""

    # 1. 从本地路由表获取α个最近节点
    closest_nodes = self.routing_table.find_closest_nodes(target_id, self.alpha)
    contacted = set(closest_nodes)

    while True:
        # 2. 并行向α个未查询的最近节点发送find_node请求
        pending_tasks = []
        for node in closest_nodes[:self.alpha]:
            if node not in contacted:
                task = asyncio.create_task(self.send_find_node(node, target_id))
                pending_tasks.append(task)
                contacted.add(node)

        if not pending_tasks:
            break

        # 3. 等待响应
        responses = await asyncio.gather(*pending_tasks, return_exceptions=True)

        # 4. 处理响应，收集新节点
        new_nodes = []
        for response in responses:
            if not isinstance(response, Exception):
                new_nodes.extend(response.nodes)

        # 5. 更新最近节点列表
        for new_node in new_nodes:
            if new_node not in closest_nodes:
                closest_nodes.append(new_node)

        # 6. 按距离排序，保留k个最近的
        closest_nodes.sort(key=lambda n: n.distance_to(target_id))
        closest_nodes = closest_nodes[:self.k]

        # 7. 如果找到了目标节点或没有更近的节点，则停止
        if any(node.node_id == target_id for node in closest_nodes):
            break

        # 8. 检查是否还有未查询的更近节点
        uncontacted_closest = [
            node for node in closest_nodes
            if node not in contacted
        ]

        if not uncontacted_closest:
            break

    return closest_nodes[:self.k]
```

**GET_PEERS算法**：
```python
async def iterative_get_peers(self, info_hash: bytes) -> Tuple[List[Peer], List[Node]]:
    """迭代查找指定info_hash的peers"""

    closest_nodes = self.routing_table.find_closest_nodes(info_hash, self.alpha)
    contacted = set()
    discovered_peers = []

    while True:
        # 并行查询最近的节点
        pending_tasks = []
        for node in closest_nodes[:self.alpha]:
            if node not in contacted:
                task = asyncio.create_task(self.send_get_peers(node, info_hash))
                pending_tasks.append(task)
                contacted.add(node)

        if not pending_tasks:
            break

        responses = await asyncio.gather(*pending_tasks, return_exceptions=True)

        # 处理响应
        new_nodes = []
        for response in responses:
            if not isinstance(response, Exception):
                # 收集peers
                if response.peers:
                    discovered_peers.extend(response.peers)

                # 收集新节点
                if response.nodes:
                    new_nodes.extend(response.nodes)

        # 如果找到了peers，直接返回
        if discovered_peers:
            return discovered_peers, closest_nodes

        # 否则继续查找更近的节点
        for new_node in new_nodes:
            if new_node not in closest_nodes:
                closest_nodes.append(new_node)

        closest_nodes.sort(key=lambda n: n.distance_to(info_hash))
        closest_nodes = closest_nodes[:self.k]

        # 检查是否还有未查询的更近节点
        uncontacted_closest = [
            node for node in closest_nodes
            if node not in contacted
        ]

        if not uncontacted_closest:
            break

    return discovered_peers, closest_nodes[:self.k]
```

#### 键值对存储策略

Kademlia中每个节点负责存储与其ID"接近"的键值对：

**存储规则**：
1. **距离决定存储**：键值对存储在距离键最近的k个节点上
2. **复制因子**：每个键值对复制k份（k=8）
3. **缓存机制**：查询路径上的节点会缓存键值对

**存储位置计算**：
```python
def should_store_key(self, key: bytes) -> bool:
    """判断是否应该存储指定键"""
    distance = int.from_bytes(self.node_id, 'big') ^ int.from_bytes(key, 'big')

    # 计算需要存储的节点数
    storage_nodes = []

    # 找到距离键最近的k个节点
    all_nodes = self.get_all_known_nodes()
    all_nodes.sort(key=lambda n: n.distance_to(key))

    # 如果当前节点在最近的k个节点中，则需要存储
    closest_k = all_nodes[:self.k]
    return any(n.node_id == self.node_id for n in closest_k)

def get_responsible_nodes(self, key: bytes) -> List[Node]:
    """获取负责存储指定键的节点"""
    all_nodes = self.get_all_known_nodes()
    all_nodes.sort(key=lambda n: n.distance_to(key))
    return all_nodes[:self.k]
```

**存储流程示例**：
```
假设键K = 101001... (160位)
1. 计算每个节点到K的XOR距离
2. 找到距离最近的8个节点
3. 将键值对存储到这8个节点上
4. 每个节点定期刷新存储的键值对
```

#### 键值对刷新和发布

**STORE操作**：
```python
async def store_key_value(self, key: bytes, value: bytes) -> bool:
    """存储键值对到DHT网络"""

    # 1. 找到负责存储的节点
    responsible_nodes = await self.iterative_find_node(key)

    # 2. 向每个节点发送store请求
    store_tasks = []
    for node in responsible_nodes:
        task = asyncio.create_task(self.send_store(node, key, value))
        store_tasks.append(task)

    # 3. 等待存储确认
    responses = await asyncio.gather(*store_tasks, return_exceptions=True)

    # 4. 统计成功存储的数量
    success_count = sum(1 for r in responses if not isinstance(r, Exception))
    return success_count >= (self.k // 2 + 1)  # 至少一半成功
```

**键值对刷新机制**：
```python
async def refresh_stored_keys(self):
    """刷新存储的键值对"""
    current_time = time.time()

    for key, (value, timestamp) in self.stored_keys.items():
        # 每小时刷新一次
        if current_time - timestamp > 3600:
            # 重新发布键值对
            responsible_nodes = await self.iterative_find_node(key)
            for node in responsible_nodes:
                await self.send_store(node, key, value)

            # 更新时间戳
            self.stored_keys[key] = (value, current_time)
```

#### 并行查询优化

**α参数的作用**：
- **α=1**：串行查询，延迟高但带宽消耗低
- **α=3**：平衡的选择，BitTorrent DHT采用
- **α=8**：并行度最高，延迟最低但带宽消耗大

**自适应α**：
```python
def adaptive_alpha(self, network_quality: float) -> int:
    """根据网络质量动态调整并行度"""
    if network_quality > 0.8:  # 网络质量好
        return min(8, self.alpha * 2)
    elif network_quality < 0.3:  # 网络质量差
        return max(1, self.alpha // 2)
    else:
        return self.alpha
```

#### 路由表维护

**节点更新策略**：
```python
def update_node_in_bucket(self, node: Node):
    """更新bucket中的节点信息"""
    bucket = self.get_bucket_for_node(node)

    # 检查节点是否已存在
    for existing_node in bucket.nodes:
        if existing_node.node_id == node.node_id:
            # 移到bucket末尾（LRU策略）
            bucket.nodes.remove(existing_node)
            bucket.nodes.append(node)
            return True

    # bucket未满，直接添加
    if len(bucket.nodes) < self.k:
        bucket.nodes.append(node)
        return True

    # bucket已满，ping最旧的节点
    oldest_node = bucket.nodes[0]
    if self.ping_node(oldest_node):
        # 最旧节点仍有响应，替换它
        bucket.nodes.remove(oldest_node)
        bucket.nodes.append(node)
        return False
    else:
        # 最旧节点无响应，移除它
        bucket.nodes.remove(oldest_node)
        bucket.nodes.append(node)
        return True
```

**定期维护**：
```python
async def periodic_maintenance(self):
    """定期维护路由表和存储数据"""
    while True:
        try:
            # 刷新未查询的bucket
            for i, bucket in enumerate(self.routing_table.buckets):
                if bucket.is_stale():  # 超过1小时未更新
                    random_target = self.generate_random_id_for_bucket(i)
                    await self.iterative_find_node(random_target)

            # 刷新存储的键值对
            await self.refresh_stored_keys()

            # 清理过期数据
            await self.cleanup_expired_data()

            await asyncio.sleep(3600)  # 每小时执行一次维护

        except Exception as e:
            logging.error(f"路由表维护错误: {e}")
            await asyncio.sleep(300)
```

#### 算法复杂度分析

**查找复杂度**：
- 时间复杂度：O(log n)
- 空间复杂度：O(k log n)
- 消息复杂度：O(log n)

**为什么是对数复杂度**：
每次查询都能将搜索空间减半，类似于二分查找，因此需要O(log n)步就能找到目标。

**容错性**：
- 每个key存储在k个节点上
- 最多可以容忍k-1个节点失效
- 查询时自动绕过失效节点

这种设计使得Kademlia在P2P环境中具有高可扩展性、高容错性和高效的查找性能。

## DHT协议详解

### 节点ID和距离计算

每个DHT节点都有一个160位的唯一标识符（Node ID），通常通过SHA-1哈希算法生成。节点间距离通过异或运算计算：

```
distance(A, B) = A XOR B
```

### 路由表结构

DHT路由表分为k个bucket，每个bucket包含距离相近的节点：

- Bucket 0：距离范围 [0, 2^1)
- Bucket 1：距离范围 [2^1, 2^2)
- ...
- Bucket k-1：距离范围 [2^(k-1), 2^k)

### 主要操作类型

#### PING - 节点存活检测

**请求格式**：
```
{
  "t": "随机事务ID",
  "y": "q",
  "q": "ping",
  "a": {"id": "发送者节点ID"}
}
```

**响应格式**：
```
{
  "t": "相同的事务ID",
  "y": "r",
  "r": {"id": "响应者节点ID"}
}
```

**错误响应**：
```
{
  "t": "相同的事务ID",
  "y": "e",
  "e": [201, "Generic Error"]
}
```

#### FIND_NODE - 查找节点

**请求格式**：
```
{
  "t": "随机事务ID",
  "y": "q",
  "q": "find_node",
  "a": {
    "id": "发送者节点ID",
    "target": "目标节点ID"
  }
}
```

**响应格式**：
```
{
  "t": "相同的事务ID",
  "y": "r",
  "r": {
    "id": "响应者节点ID",
    "nodes": "压缩的节点信息"
  }
}
```

**nodes字段格式说明**：
- 每个节点占用26字节：4字节IP + 2字节端口 + 20字节节点ID
- 例如：`\xc0\xa8\x01\x01\x1f\x90` + `20字节节点ID`

**错误响应**：
```
{
  "t": "相同的事务ID",
  "y": "e",
  "e": [202, "Server Error"]
}
```

#### GET_PEERS - 获取种子节点

**请求格式**：
```
{
  "t": "随机事务ID",
  "y": "q",
  "q": "get_peers",
  "a": {
    "id": "发送者节点ID",
    "info_hash": "种子info_hash"
  }
}
```

**响应格式（有peers）**：
```
{
  "t": "相同的事务ID",
  "y": "r",
  "r": {
    "id": "响应者节点ID",
    "token": "返回令牌",
    "values": ["peer1信息", "peer2信息"]
  }
}
```

**响应格式（无peers，返回最近节点）**：
```
{
  "t": "相同的事务ID",
  "y": "r",
  "r": {
    "id": "响应者节点ID",
    "token": "返回令牌",
    "nodes": "压缩的节点信息"
  }
}
```

**values字段格式说明**：
- 每个peer占用6字节：4字节IP + 2字节端口
- 例如：`\xc0\xa8\x01\x02\x1f\x91` 表示 `192.168.1.2:8081`

#### ANNOUNCE_PEER - 宣告节点

**请求格式**：
```
{
  "t": "随机事务ID",
  "y": "q",
  "q": "announce_peer",
  "a": {
    "id": "发送者节点ID",
    "info_hash": "种子info_hash",
    "port": 端口号,
    "token": "从get_peers获得的令牌",
    "implied_port": 0或1
  }
}
```

**响应格式**：
```
{
  "t": "相同的事务ID",
  "y": "r",
  "r": {"id": "响应者节点ID"}
}
```

#### 错误代码说明

常见错误代码：
- `201` - Generic Error（通用错误）
- `202` - Server Error（服务器错误）
- `203` - Protocol Error（协议错误，如错误的消息格式）
- `204` - Method Unknown（未知方法）
- `205` - Token not found（令牌无效或过期）
- `206` - Argument error（参数错误）
- `207` - Missing argument（缺少参数）
- `208` - Invalid argument（无效参数）
- `209` - Logic error（逻辑错误）
- `210` - Try again later（请稍后重试）

## 爬虫实现策略

### 主动爬取策略

主动爬取通过遍历DHT网络空间来发现节点：

```python
class DHTCrawler:
    def __init__(self, port=6881):
        self.port = port
        self.node_id = self.generate_node_id()
        self.routing_table = RoutingTable()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', port))

    def generate_node_id(self):
        """生成随机160位节点ID"""
        random_bytes = os.urandom(20)
        return hashlib.sha1(random_bytes).digest()

    def start_crawling(self):
        """开始爬取DHT网络"""
        # 连接已知节点
        bootstrap_nodes = [
            ("router.bittorrent.com", 6881),
            ("dht.transmissionbt.com", 6881),
            ("router.utorrent.com", 6881)
        ]

        for node in bootstrap_nodes:
            self.ping_node(node)

        # 开始主动发现
        self.active_discovery()
```

### 被动监听策略

被动监听通过响应其他节点的请求来收集信息：

```python
def start_listening(self):
    """开始被动监听"""
    while True:
        try:
            data, addr = self.socket.recvfrom(2048)
            self.handle_message(data, addr)
        except Exception as e:
            logging.error(f"接收消息错误: {e}")

def handle_message(self, data, addr):
    """处理接收到的消息"""
    try:
        message = bdecode(data)

        if message.get('y') == 'q':  # 请求消息
            self.handle_request(message, addr)
        elif message.get('y') == 'r':  # 响应消息
            self.handle_response(message, addr)

    except Exception as e:
        logging.error(f"消息处理错误: {e}")
```

## 完整实现代码

### 消息编解码模块

可以参看另一篇文章bencode编码的实现

### 路由表实现

```python
import time
from collections import deque
from typing import List, Optional

class Node:
    def __init__(self, node_id: bytes, ip: str, port: int):
        self.node_id = node_id
        self.ip = ip
        self.port = port
        self.last_seen = time.time()
        self.failed_queries = 0
        self.questions_to_node = 0

    def update_last_seen(self):
        self.last_seen = time.time()
        self.failed_queries = 0

    def increment_failed_queries(self):
        self.failed_queries += 1

    def is_good(self) -> bool:
        return (self.failed_queries == 0 and
                self.questions_to_node > 0 and
                time.time() - self.last_seen < 900)  # 15分钟

    def distance_to(self, target_id: bytes) -> int:
        """计算到目标节点的距离"""
        return int.from_bytes(self.node_id, 'big') ^ int.from_bytes(target_id, 'big')

class KBucket:
    def __init__(self, max_size: int = 8):
        self.max_size = max_size
        self.nodes = deque()
        self.replacement_cache = deque()

    def add_node(self, node: Node) -> bool:
        """添加节点到bucket"""
        # 检查是否已存在
        for i, existing_node in enumerate(self.nodes):
            if existing_node.node_id == node.node_id:
                # 移到末尾（最近使用）
                self.nodes.remove(existing_node)
                self.nodes.append(node)
                return True

        # 检查是否还有空间
        if len(self.nodes) < self.max_size:
            self.nodes.append(node)
            return True

        # 添加到替换缓存
        self.replacement_cache.append(node)
        return False

    def remove_node(self, node_id: bytes):
        """从bucket中移除节点"""
        for i, node in enumerate(self.nodes):
            if node.node_id == node_id:
                self.nodes.remove(node)
                # 从替换缓存中添加一个节点
                if self.replacement_cache:
                    replacement = self.replacement_cache.popleft()
                    self.nodes.append(replacement)
                break

    def get_good_nodes(self) -> List[Node]:
        """获取所有活跃节点"""
        return [node for node in self.nodes if node.is_good()]

class RoutingTable:
    def __init__(self, node_id: bytes):
        self.node_id = node_id
        self.buckets = [KBucket() for _ in range(160)]  # 160位ID

    def get_bucket_index(self, target_id: bytes) -> int:
        """获取目标节点对应的bucket索引"""
        distance = int.from_bytes(self.node_id, 'big') ^ int.from_bytes(target_id, 'big')
        return distance.bit_length() - 1 if distance != 0 else 0

    def add_node(self, node: Node) -> bool:
        """添加节点到路由表"""
        if node.node_id == self.node_id:
            return False

        bucket_index = self.get_bucket_index(node.node_id)
        return self.buckets[bucket_index].add_node(node)

    def find_closest_nodes(self, target_id: bytes, count: int = 8) -> List[Node]:
        """查找距离目标最近的节点"""
        bucket_index = self.get_bucket_index(target_id)
        closest_nodes = []

        # 从目标bucket开始，向两侧搜索
        for i in range(max(0, bucket_index - 1), min(160, bucket_index + 2)):
            bucket_nodes = sorted(self.buckets[i].nodes,
                                key=lambda n: n.distance_to(target_id))
            closest_nodes.extend(bucket_nodes)

        # 按距离排序并返回前count个
        closest_nodes.sort(key=lambda n: n.distance_to(target_id))
        return closest_nodes[:count]
```

### 主要爬虫逻辑

```python
import asyncio
import random
import time
import logging
from typing import Dict, Set, Tuple

class DHTCrawler:
    def __init__(self, port: int = 6881):
        self.port = port
        self.node_id = self.generate_node_id()
        self.routing_table = RoutingTable(self.node_id)
        self.socket = None
        self.running = False
        self.discovered_peers: Set[str] = set()
        self.discovered_info_hashes: Set[bytes] = set()

        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def generate_node_id(self) -> bytes:
        """生成随机160位节点ID"""
        random_bytes = random.getrandbits(160).to_bytes(20, 'big')
        return hashlib.sha1(random_bytes).digest()

    async def start(self):
        """启动爬虫"""
        self.socket = asyncio.socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', self.port))
        self.socket.setblocking(False)

        self.running = True

        # 启动监听任务
        listen_task = asyncio.create_task(self.listen_for_messages())

        # 启动主动发现任务
        discovery_task = asyncio.create_task(self.active_discovery())

        # 启动路由表维护任务
        maintenance_task = asyncio.create_task(self.maintain_routing_table())

        self.logger.info(f"DHT爬虫已启动，端口: {self.port}")
        self.logger.info(f"节点ID: {self.node_id.hex()}")

        try:
            await asyncio.gather(listen_task, discovery_task, maintenance_task)
        except KeyboardInterrupt:
            self.logger.info("正在停止爬虫...")
            self.running = False

    async def listen_for_messages(self):
        """监听网络消息"""
        while self.running:
            try:
                data, addr = await self.socket.recvfrom(2048)
                asyncio.create_task(self.handle_message(data, addr))
            except Exception as e:
                if self.running:
                    self.logger.error(f"消息监听错误: {e}")
                await asyncio.sleep(0.1)

    async def handle_message(self, data: bytes, addr: Tuple[str, int]):
        """处理接收到的消息"""
        try:
            message = bdecode(data)
            self.logger.debug(f"收到消息: {message}")

            if message.get('y') == 'q':  # 请求消息
                await self.handle_request(message, addr)
            elif message.get('y') == 'r':  # 响应消息
                await self.handle_response(message, addr)
            elif message.get('y') == 'e':  # 错误消息
                self.logger.warning(f"收到错误消息: {message} from {addr}")

        except Exception as e:
            self.logger.error(f"消息处理错误: {e}")

    async def handle_request(self, message: Dict, addr: Tuple[str, int]):
        """处理请求消息"""
        query_type = message.get('q')
        args = message.get('a', {})
        transaction_id = message.get('t')

        # 更新路由表
        node_id = args.get('id')
        if node_id:
            node = Node(node_id, addr[0], addr[1])
            node.update_last_seen()
            self.routing_table.add_node(node)

        # 根据查询类型处理
        if query_type == 'ping':
            response = self.create_response(transaction_id, {'id': self.node_id})
        elif query_type == 'find_node':
            target = args.get('target')
            closest_nodes = self.routing_table.find_closest_nodes(target)
            nodes_info = [(n.ip.encode(), n.port, n.node_id) for n in closest_nodes]
            response = self.create_response(transaction_id, {
                'id': self.node_id,
                'nodes': self.encode_nodes(nodes_info)
            })
        elif query_type == 'get_peers':
            info_hash = args.get('info_hash')
            self.discovered_info_hashes.add(info_hash)

            # 这里没有实际peers，返回token
            token = self.generate_token(addr)
            response = self.create_response(transaction_id, {
                'id': self.node_id,
                'token': token,
                'nodes': self.encode_nodes(self.get_closest_nodes())
            })
        else:
            return

        await self.send_message(response, addr)

    async def handle_response(self, message: Dict, addr: Tuple[str, int]):
        """处理响应消息"""
        response_data = message.get('r', {})

        # 更新路由表
        node_id = response_data.get('id')
        if node_id:
            node = Node(node_id, addr[0], addr[1])
            node.update_last_seen()
            self.routing_table.add_node(node)

        # 处理nodes信息
        if 'nodes' in response_data:
            nodes_data = self.decode_nodes(response_data['nodes'])
            for ip, port, node_id in nodes_data:
                new_node = Node(node_id, ip.decode(), port)
                self.routing_table.add_node(new_node)

        # 处理peers信息
        if 'values' in response_data:
            peers = response_data['values']
            for peer in peers:
                peer_str = f"{peer[0]}:{peer[1]}"
                self.discovered_peers.add(peer_str)

    async def active_discovery(self):
        """主动发现节点"""
        # 引导节点列表
        bootstrap_nodes = [
            ("router.bittorrent.com", 6881),
            ("dht.transmissionbt.com", 6881),
            ("router.utorrent.com", 6881)
        ]

        # 连接引导节点
        for node in bootstrap_nodes:
            await self.ping_node(node)
            await asyncio.sleep(0.1)

        # 持续发现新节点
        while self.running:
            try:
                # 生成随机目标ID进行find_node查询
                target_id = random.getrandbits(160).to_bytes(20, 'big')
                await self.find_node(target_id)

                # 每10秒执行一次发现
                await asyncio.sleep(10)

            except Exception as e:
                self.logger.error(f"主动发现错误: {e}")
                await asyncio.sleep(5)

    async def ping_node(self, addr: Tuple[str, int]):
        """向节点发送ping请求"""
        transaction_id = self.generate_transaction_id()
        message = self.create_request('ping', {
            'id': self.node_id
        }, transaction_id)

        await self.send_message(message, addr)

    async def find_node(self, target_id: bytes):
        """查找指定ID的节点"""
        closest_nodes = self.routing_table.find_closest_nodes(target_id, 3)

        for node in closest_nodes:
            transaction_id = self.generate_transaction_id()
            message = self.create_request('find_node', {
                'id': self.node_id,
                'target': target_id
            }, transaction_id)

            addr = (node.ip, node.port)
            await self.send_message(message, addr)

    async def get_peers(self, info_hash: bytes):
        """获取指定种子的peers"""
        closest_nodes = self.routing_table.find_closest_nodes(info_hash, 3)

        for node in closest_nodes:
            transaction_id = self.generate_transaction_id()
            message = self.create_request('get_peers', {
                'id': self.node_id,
                'info_hash': info_hash
            }, transaction_id)

            addr = (node.ip, node.port)
            await self.send_message(message, addr)

    async def send_message(self, message: Dict, addr: Tuple[str, int]):
        """发送消息到指定地址"""
        try:
            data = bencode(message)
            self.socket.sendto(data, addr)
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")

    def create_request(self, query_type: str, args: Dict, transaction_id: bytes) -> Dict:
        """创建请求消息"""
        return {
            't': transaction_id,
            'y': 'q',
            'q': query_type,
            'a': args
        }

    def create_response(self, transaction_id: bytes, data: Dict) -> Dict:
        """创建响应消息"""
        return {
            't': transaction_id,
            'y': 'r',
            'r': data
        }

    def generate_transaction_id(self) -> bytes:
        """生成事务ID"""
        return random.getrandbits(32).to_bytes(4, 'big')

    def generate_token(self, addr: Tuple[str, int]) -> bytes:
        """生成token"""
        token_data = f"{addr[0]}:{addr[1]}".encode()
        return hashlib.sha1(token_data).digest()[:4]

    def encode_nodes(self, nodes: List[Tuple[bytes, int, bytes]]) -> bytes:
        """编码节点信息"""
        result = b''
        for ip, port, node_id in nodes:
            result += ip + struct.pack('!H', port) + node_id
        return result

    def decode_nodes(self, data: bytes) -> List[Tuple[bytes, int, bytes]]:
        """解码节点信息"""
        nodes = []
        for i in range(0, len(data), 26):
            if i + 26 <= len(data):
                ip = data[i:i+4]
                port = struct.unpack('!H', data[i+4:i+6])[0]
                node_id = data[i+6:i+26]
                nodes.append((ip, port, node_id))
        return nodes

    def get_closest_nodes(self) -> List[Tuple[bytes, int, bytes]]:
        """获取最近的节点"""
        closest_nodes = []
        for bucket in self.routing_table.buckets:
            for node in bucket.get_good_nodes():
                closest_nodes.append((node.ip.encode(), node.port, node.node_id))
        return closest_nodes[:8]

    async def maintain_routing_table(self):
        """维护路由表"""
        while self.running:
            try:
                current_time = time.time()

                # 移除过期节点
                for bucket in self.routing_table.buckets:
                    expired_nodes = []
                    for node in bucket.nodes:
                        if current_time - node.last_seen > 1800:  # 30分钟
                            expired_nodes.append(node)

                    for node in expired_nodes:
                        bucket.remove_node(node.node_id)

                # 打印统计信息
                total_nodes = sum(len(bucket.nodes) for bucket in self.routing_table.buckets)
                self.logger.info(f"路由表节点总数: {total_nodes}")
                self.logger.info(f"发现的peers数量: {len(self.discovered_peers)}")
                self.logger.info(f"发现的info_hash数量: {len(self.discovered_info_hashes)}")

                await asyncio.sleep(300)  # 5分钟维护一次

            except Exception as e:
                self.logger.error(f"路由表维护错误: {e}")
                await asyncio.sleep(60)

    def get_statistics(self) -> Dict:
        """获取爬虫统计信息"""
        return {
            'total_nodes': sum(len(bucket.nodes) for bucket in self.routing_table.buckets),
            'discovered_peers': len(self.discovered_peers),
            'discovered_info_hashes': len(self.discovered_info_hashes),
            'node_id': self.node_id.hex(),
            'port': self.port
        }

# 使用示例
async def main():
    crawler = DHTCrawler(port=6881)
    try:
        await crawler.start()
    except KeyboardInterrupt:
        print("爬虫已停止")

if __name__ == "__main__":
    asyncio.run(main())
```

## 优化策略

### 性能优化

1. **并发控制**：限制同时发送的请求数量
2. **请求去重**：避免重复查询相同的info_hash
3. **连接池**：复用网络连接
4. **缓存机制**：缓存频繁查询的结果

```python
class RateLimiter:
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    async def acquire(self):
        """获取请求许可"""
        current_time = time.time()

        # 清理过期请求
        self.requests = [req_time for req_time in self.requests
                        if current_time - req_time < self.time_window]

        # 检查是否超过限制
        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (current_time - self.requests[0])
            await asyncio.sleep(sleep_time)
            return await self.acquire()

        self.requests.append(current_time)
```

### 存储优化

对于大规模爬取，需要考虑数据存储策略：

```python
import sqlite3
import json
from datetime import datetime

class DHTDatabase:
    def __init__(self, db_path: str = "dht_crawler.db"):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        """创建数据表"""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                ip TEXT,
                port INTEGER,
                last_seen REAL,
                failed_queries INTEGER DEFAULT 0
            )
        ''')

        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS peers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                info_hash TEXT,
                peer_address TEXT,
                discovered_at REAL
            )
        ''')

        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS info_hashes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                info_hash TEXT,
                discovered_at REAL,
                peer_count INTEGER DEFAULT 0
            )
        ''')

        self.conn.commit()

    def save_node(self, node_id: bytes, ip: str, port: int, last_seen: float):
        """保存节点信息"""
        self.conn.execute('''
            INSERT OR REPLACE INTO nodes (id, ip, port, last_seen)
            VALUES (?, ?, ?, ?)
        ''', (node_id.hex(), ip, port, last_seen))
        self.conn.commit()

    def save_peer(self, info_hash: bytes, peer_address: str):
        """保存peer信息"""
        self.conn.execute('''
            INSERT INTO peers (info_hash, peer_address, discovered_at)
            VALUES (?, ?, ?)
        ''', (info_hash.hex(), peer_address, time.time()))
        self.conn.commit()
```

## 总结

BitTorrent DHT网络爬虫是一个复杂的分布式系统项目，需要深入理解P2P网络协议、网络编程和并发处理。

在实际应用中，需要根据具体需求调整爬虫策略，同时确保遵循相关法律法规和网络道德准则。

## 参考资料

- [BitTorrent DHT Protocol Specification](https://www.bittorrent.org/beps/bep_0005.html)
- [Kademlia: A Peer-to-peer Information System Based on the XOR Metric](https://pdos.csail.mit.edu/~petar/papers/maymounkov-kademlia-lncs.pdf)
- [libtorrent DHT Implementation](https://github.com/arvidn/libtorrent)
