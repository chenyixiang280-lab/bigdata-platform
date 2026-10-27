# 业务口径与历史规则差异

来源：项目原 `dw-sql-rules.zip` 的SKILL第1—5节、`src/bigdata_agent/business/knowledge.py` 的RULE_NOTES/EXCLUDED，以及2026-09—10月用户确认。2026-10-27离线整理，未重新核验生产口径。使用前读取当前绑定包的真实字段、注释、分区和SQL版本；以下是本项目业务约定，不是跨企业数据库标准。

## 适用口径

- 门店销售/交易分析默认主营：存在对应字段且用户未另指定范围时使用 `busi_unit_lev1_name = '主营'`。线上、DTP、加盟或全渠道分析按用户范围另定，不机械套用。
- 一般销售使用 `acco_amt`；综合毛利来源 `dm_com.comprehensive_profit_base_data_dfp` 的销售口径使用 `sale_amt`，补偿前毛利候选 `before_comp_profit`，含市场费用综合毛利候选 `comperhensive_profit_included_mkt_payout`。先核字段及口径；历史“T-2/74字段”不是当前更新时效或结构保证。
- X大类指 `goods_code LIKE 'X%'`，不是任意位置包含X。
- 正常经营直营门店的既有业务口径：`busi_ascr_code IN ('1','4')`，`shop_age_type_code IN ('1','2','3','4','8')`，业态多值含01。字段是code而非name；先确认当前字段含义、快照与多值分隔符。已确认逗号分隔时，Spark用 `array_contains(split(format_code, ','), '01')`，Trino用 `contains(split(format_code, ','), '01')`，避免子串误匹配。
- 本项目类别分组使用 `strategy_classify_name`（三级策略分类），不使用历史规则禁用的 `goods_class_name`。发现当前目标结构不适用时报告冲突，不猜替代列。
- 字段注释带“废弃/停用”时，不用于新查询；可读历史SQL解释旧逻辑。注释指向的新表/列只是替代线索，必须再核结构、Join键与粒度。例如归档 `dwd.dim_shop_info_dfn.is_med_insu_coor` 注释指向 `dws.dws_med_insu_tag_dfp`，不能直接沿用旧列或猜新列名。
- 日期维表候选 `dim.dim_date_dfn`，先核 `date_id` 类型与格式、周/月/季度/节假日字段。跨年周必须明确ISO周与周所属年，验证年末年初边界。旧规则的 `YYYY-'W'ww` 不是跨引擎通用写法，也不保证当前Spark版本支持；不要把日历年和ISO周直接拼接。
- 输出说明与列别名用中文，忠实表达字段及指标口径；派生指标给准确名称，不强制逐字复制无关DDL注释。Spark标识符用反引号，Trino用双引号，旧Presto单引号别名规则不再沿用。

## 必须披露的冲突

| 主题 | 已有证据和处理 |
|---|---|
| 综合毛利分区 | 旧DDL写DATE，旧skill要求dt。读取当前包的分区字段与类型，不能认为date等于dt；业务日期与物理分区分别说明。 |
| 小票补贴 | `dws.dws_trans_posbill_detail_extention_dip.acco_amt` 的旧DDL含补贴，CSV新注释剔除平台补贴；需按适用时点/当前SQL确认，不强行选DDL。 |
| 主营跨期 | 小票旧注释记2026年前剔除店转、2026年起包含店转；不能外推综合毛利 `busi_unit_lev1_code=3` 两期自动可比。 |
| 组织与子店 | 当前名单回看、历史组织、同店可比是不同口径；事实dept_id须映射shop_code。子店同期无记录不补零或父店金额、不删除其已有记录；无同期不算增幅。 |
| 后缀和热度 | dfn/dfp/dip等是命名线索，不能证明有无分区、全历史或覆盖。hotValue与旧HU/H0—H5档位不同；没有热度不是无权限，新包不伪造hotTier。 |

## 历史执行排除清单

当前项目旧Knowledge执行门禁仍排除以下8表并拒绝HU表。离线工具允许展示其证据，但新skill不会撤销原执行门禁。前四项的dm_cate同名表只是候选，须精确核结构、来源、粒度及权限后使用。

| 排除表 | 已记录替代线索 |
|---|---|
| dm_del.war_zone_goods_stock_sales_dfp | dm_cate.war_zone_goods_stock_sales_dfp |
| dm_del.shop_goods_price_group_dfp | dm_cate.shop_goods_price_group_dfp |
| dm_del.group_goods_stock_sales_dfp | dm_cate.group_goods_stock_sales_dfp |
| dm_del.shop_price_group_dfp | dm_cate.shop_price_group_dfp |
| dm_del.hn_war_zone_n_insu_goods_stock_sales_dfp | 未指定 |
| dm_del.js_goods_stock_sales_dfp | 未指定 |
| dm_del.shop_stock_analysis_dfp | 未指定 |
| dm_del.group_goods_stock_sales_cut_dfp | 未指定 |
