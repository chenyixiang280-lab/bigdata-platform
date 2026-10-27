# 当前平台适配与现场证据

适配平台入口为`https://data.lbxcn.com`。实际运行以项目`config/platform.yaml`为准；使用项目`.venv`、Windows、Python3.12和有头Microsoft Edge专用Profile。Skill不存Profile路径、Cookie、账号、Token或环境凭据，不复制日常浏览器会话。

项目根目录由用户提供或当前工作区确定；先看AGENTS.md、docs/PROJECT_STATE.md、docs/TODO.md、接口发现和决策文件、Git状态。旧P2E隔离门禁、业务执行卡和本次元数据授权各有范围，不能互相替代。技能是可复用流程，不是永久执行授权。

## 已观察的只读合同（2026-10-25前证据）

| 用途 | 已观察路径 | 注意 |
|---|---|---|
| 数据地图列表 | `/api/metadata-management/tableInfo/getAllTables` | 列表不是业务查询授权清单 |
| 即席查询可见清单 | `/api/metadata-management/tableInfo/getAuthList` | 记录账号、开发组、清单时点 |
| 详情 | `/api/metadata-management/tableInfo/getTableInfo` | 参数以实际UI请求为准，表原生ID需核对 |
| 字段 | `/api/metadata-management/fieldsInfo/getFieldInfo` | 普通字段与分区分开 |
| 资产说明/SQL | `/api/metadata-management/assetNotes/getList` | 记录版本、latest、来源时点；默认列表不等于全部历史 |
| 一层血缘 | `/api/metadata-management/bloodRelation/getDiagram` | 按根表ID验证，保留方向；空返回不是无血缘证明 |
| 任务详情 | `/api/web-scheduler/processDefinition/getTaskDetails` | taskId来自真实表关联，核对组与权限 |
| 任务源码 | `/api/web-scheduler/processDefinition/getTaskScript` | 只读源证据，不执行 |

这些路径用于识别真实请求，不是允许直接重放任意请求的清单。未观察的参数、请求体和枚举仍需正常页面验证。

直接BrowserContext.request曾丢失开发组语义，导致正常UI可见而直连显示NO_PERMISSION/空返回。必须先对照当前UI；采用当前浏览器工具支持、已验证等价且不读取认证头的会话请求路径。不能因为直连接口返回SQL就绕过UI权限。

任务可见性已观察为OWNER/EDITABLE可读；READABLE要求ONLINE，READABLE+OFFLINE在查看页拒绝；NO_PERMISSION不读源码。切换当前账号已有组必须使用正常可见控件，记录来源组，结束恢复原约定组（当前项目为商品规划组）。

## 平稳刷新

授权范围内单并发，读取完成后平稳间隔，当前参考0.6秒；429遵守Retry-After，暂时性5xx/断连退避并降低速率。成功组件复用，失败证据保留，按表/组件保存断点。持续错误时停止有问题的分支，独立本地工作继续。

身份、原生ID、响应合同变化先核实；认证失效请求人工登录；权限拒绝不绕过。不得读取示例数据接口，不运行SQL、不更新资产文档、不收藏或修改平台。接口空返回必要时用同组同ID正常页面定点核对，不机械重刷全表。

网络元数据先走项目集中脱敏；归档SQL/说明是用户明确授权的源码证据例外，仍做敏感模式和URL脱敏检查，排除业务行与认证信息。新环境用其自身的脱敏机制，不能直接落盘未经检查的响应。
