# Node Parser / 订阅节点聚合器

一个基于 GitHub Actions 自动运行的订阅解析工具，支持从多个订阅链接（机场订阅）中提取节点，自动去重、地理信息标记，并生成多种格式的配置文件，方便 Clash、v2rayN、Nekobox 等客户端使用。

项目特点：
- 每日自动更新（北京时间晚上 00:00 执行）
- 支持 VMess、VLESS、Shadowsocks、Trojan、Hysteria2 等主流协议
- 自动添加国旗 + 中文地区名称 + 独特短ID（节点名称示例：🇨🇳 中国）
- 过滤流量耗尽或过期的订阅
- 输出 Clash 配置文件（带自动测速分组）、Base64 编码的 v2ray 订阅、纯节点列表
