# 大数据平台 Skill

面向本项目的大数据平台查表、字段/分区核对、血缘与SQL追溯、查询编写、任务创建准备及知识包更新。技能名：`bigdata-platform`。

本仓库及知识包为**私有内部资料**。不公开、不镜像到公开仓库。知识包有表结构、热度、资产说明、表级血缘和可见SQL，没有业务查询结果、认证凭据或浏览器Profile。

## 已实现与使用

- 可执行：纯Python离线查表/字段检索、一层血缘、SQL/说明读取、完整性验证、新旧快照差异与版本绑定。
- 已整理：真实查询的字段/粒度/分区/权限规则、专用会话与元数据采集策略、任务草稿与平台创建/运行/发布的区分。
- 未宣称：自动创建/发布平台任务已验收、任意业务SQL可直接执行、所有表都有完整溯源，或开发页源码等于当前生产SQL。

在Codex中调用：

```text
使用 $bigdata-platform 查找含统筹销售字段的表，并说明字段和分区。
使用 $bigdata-platform 从目标表追溯某指标到小票来源，列出SQL版本和缺口。
使用 $bigdata-platform 为目标结果表准备任务草稿，先核对结构和依赖，不运行或发布。
使用 $bigdata-platform 对比新旧知识包并更新本机绑定，保留旧版本。
```

## 安装

需要Python 3.12+，离线脚本不依赖第三方包。GitHub CLI仅用于下载私有仓库/Release，凭据由CLI正常登录机制管理。

```powershell
gh repo clone chenyixiang280-lab/bigdata-platform "$env:USERPROFILE/.codex/skills/bigdata-platform"
gh release download knowledge-20261025 --repo chenyixiang280-lab/bigdata-platform --pattern "knowledge-20261025.zip*" --dir <本机知识包目录>
python "$env:USERPROFILE/.codex/skills/bigdata-platform/scripts/catalog.py" bind --archive <本机知识包目录/knowledge-20261025.zip> --sha256 ac0441a34c8fe3649207390a8f78dd21bcf4a1a2d35947c9cd7a9daffae728b7
```

路径占位符替换为本机实际目录；已有安装目录时不要覆盖或重复clone。Skill内容更新后按宿主要求重新加载技能。日常查表使用绑定，不需要登录大数据平台。

## 数据版本

知识包以2026-10-25归档为基线，组件有各自采集时点；它不是2026-10-27实时重采结果。共7,139表，2,887表SQL证据、2,318表资产说明、3,748表非空血缘。剩余缺口和历史版本状态在包内保留。

`catalog-release.json`保存当前知识包的SHA及Release定位。57MB左右知识包放在私有Release资产中，Git只维护技能、脚本和小清单。Skill版本见`VERSION`，与知识包日期独立。

## 后续更新

新表/字段/血缘变化：按 [更新流程](references/update.md) 取得新归档，执行diff、validate/bind，使用package_catalog生成分发包，发布新知识包Release，再更新清单。规则/接口变化：修改对应reference/script并验证后发布技能更新。旧包、旧绑定、旧Release保留。

不自动开启定时采集或GitHub Actions访问内网；真实查询及平台写入依当次授权。更多操作见 [SKILL.md](SKILL.md)。

## 验证

```powershell
python -m unittest discover -s tests -v
python scripts/catalog.py validate
```

专项覆盖精确身份、哈希损坏、空血缘、不执行源码、版本切换/历史保留、ID变化拒绝、分发排除日志和凭据。真实知识包另作表数、字段、血缘、源代码及分发前后逐组件对照；结果见`VALIDATION.md`。
