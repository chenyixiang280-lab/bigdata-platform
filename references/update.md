# 更新知识包与skill

## 两类版本

技能规则/脚本采用语义版本，只有行为或规则改变时升级；表结构、热度、血缘、资产SQL采用独立知识包版本。新增字段不需要把7,000多表逐一写进SKILL.md。

`catalog-release.json`记录知识包文件、SHA、来源归档SHA、覆盖及采集窗口。私有GitHub Release保存知识包，Git只存技能和小清单；不要把大ZIP、Profile、日志或本机绑定放入Git历史。

## 日常更新

1. 用户要求更新时先盘点当前包和所需范围。使用项目已验证的采集/打包流程，只补缺失或变动组件；不要重新访问已有完整证据来回答普通离线问题。
2. 新快照另存，不改原包。记录表原生ID、组件时点、来源组、版本、失败原因；旧说明可保留但不能标成现行版本。源端缺项不以旧数据遮掩。
3. 离线比较新旧包：

```powershell
python scripts/catalog.py diff --old <旧包.zip> --new <新包.zip> --output <diff.json>
python scripts/catalog.py bind --archive <新包.zip> --sha256 <新包SHA256>
```

diff区分新增、清单不再出现、原生ID变化、结构/详情/热度和溯源变化；清单不再出现不叫物理删除。bind校验成功后保存旧绑定到`.local/history/`，再切换本机指针；ID变化拒绝自动切换，先核身份。

4. 打包分发：`python scripts/package_catalog.py --source <新归档.zip> --output <新知识包.zip> --manifest <清单.json>`。输出拒绝覆盖，验证表身份、源码/正文哈希和保留文件字节。仅选择元数据和源码证据，不复制运行日志、认证范围文件、业务结果或可执行采集代码。
5. 只有授权上传的仓库可以发布。核验仍为private，创建新Release上传知识包和SHA文件，更新`catalog-release.json`。通过GitHub读回清单，并下载发布资产核对SHA；不覆盖旧Release资产。遇到权限不足保留本地包，报告具体阻塞。
6. 若发现规则或接口行为变化，先修对应参考文档/脚本，跑专项测试和skill校验，再更新Git；当前会话不得把旧授权扩成新写入范围。只更新分发副本，不把整个项目历史推上GitHub。

## 新设备与本机安装

克隆私有技能仓库到用户的skills目录，或将技能文件复制到`~/.codex/skills/bigdata-platform/`。下载`catalog-release.json`指定Release的知识包到受控本地目录；用其SHA执行bind。不要复制另一台电脑的`.local/catalog.json`路径。

知识包更新能力是按需调用流程；安装不自动启用定时抓取、GitHub Actions访问内网或后台发布。用户明确要求定时更新时再按实际工具和网络环境配置。
