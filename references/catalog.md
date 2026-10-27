# 目录、结构与溯源

## 已支持的知识包

读取 `snapshot/snapshot.json` 和 `provenance/index.json`，不依赖目录绝对路径。完整归档包和精简skill知识包均可读取；不自动兼容未知格式。

`summary`返回实际表数、结构/热度组件和原始覆盖摘要。`table`返回字段、分区、详情、热度及各组件时点。`search --fields`同时匹配字段名和注释，只返回命中表及命中字段，不全量打印目录。

`lineage`返回该表已观察的一层上下游和采集状态。需要多层时对已存在的上游表重复调用；包外节点标为引用，不能假设已取得结构或扩大平台采集。

`sources`列出资产SQL、任务源码与相关任务SQL的路径/版本。`text --kind sql|description|task`按需读取。task模式用于检查任务更名等未能直接关联的原始源码，必须保留关联状态，不把它自动当作当前表的生产逻辑。

## 证据强度

| 数据 | 可以支持 | 不可以直接支持 |
|---|---|---|
| 字段/分区元数据 | 字段存在、类型、注释、分区声明 | 业务记录数、唯一键、完整分区 |
| 热度 | 对应来源及时点的指标值 | 查询权限、跨窗口增长、质量 |
| 表级一层血缘 | 源表到目标表关系 | 每个字段公式、Join基数、当前版本 |
| 资产AI说明 | 理解与定位SQL的辅助线索 | 已验证业务口径 |
| 历史SQL | 该归档版本的逻辑 | 当前生产任务逻辑 |
| 开发/查看页源码 | 可见的任务定义代码 | 已发布版本、执行成功、业务完整性 |

任务详情和脚本先后读取，不是原子版本锁定。`production_version_verified=false`必须保留。资产接口的latest只代表接口标记；与结构快照版本相等也不能直接证明当前生产版本。

## 常见缺口

- `OBSERVED_EMPTY` / `ASSET_LIST_EMPTY_AT_ENDPOINT`：该次接口空返回，不能单独推断无血缘或无权限。
- `PERMISSION_DENIED`：该次任务读取明确拒绝；可申请任务源码只读权限。
- `SOURCE_HIDDEN_FOR_READABLE_OFFLINE`：READABLE但任务下线，正常查看页不展示源码；不能用直连接口绕过。
- `TASK_TYPE_NOT_VERIFIED_SQL`：例如MESSAGE、EXTRACTION_TASK、PYTHON_TASK；不把连接配置当作SQL补采。
- `TASK_NAME_CHANGED_REVIEW_REQUIRED`：同任务ID的名称改变；代码可能产出不同表，先核真实目标语句。
- `TASK_PERMISSION_UNCONFIRMED`：检查任务详情中的diagnostic；可能是任务接口not-found，不自动归类为拒绝或物理删除。

## 取值追溯方法

从目标指标的SELECT表达式反查中间别名，再沿INSERT目标、FROM/JOIN、CTE及子查询追到基础字段。逐层记录：输入字段、过滤、金额/数量单位、空值、去重、聚合粒度、连接键、分区和业务日期。金额作为分类条件与金额被直接累计是两回事。分清退货负数、基金支付额、商品销售额等字段的角色。

同一字段的CSV注释、DDL、资产说明或不同版本SQL冲突时，并列来源、时点和适用范围；不要用固定“DDL优先”消除冲突。结论须说明已验证到哪一层。
