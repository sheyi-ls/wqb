# wqb 能力清单

> **wqb** = 纯 BRAIN HTTP SDK（入口 ``from wqb.api import ...``）· **tools** = 工具包（入口 ``from tools.<mod>.api import ...``，依赖 wqb，不发 HTTP）  
> **不做：** machine_lib factories、RA daemon、MySQL、DV、IS checks 解析、Super Alpha API  
> **范围：** 仅列**尚无**的能力；已有能力的增强 / 健壮性 / kernel 迁移不在此列

---

# 一、wqb — 会话

- [x] 自动登录 / 过期重登（`AutoAuthSession`）
- [x] 认证 CRUD（get / post / delete / head）

# 二、wqb — 数据目录

- [x] 算子查询（`search_operators`）
- [x] 数据集：单条定位 + 筛选 + 分页
- [x] 字段：单条定位 + 筛选 + 分页

# 三、wqb — Alpha

- [x] 单条查询（`locate_alpha` / `locate_alpha_brief`）
- [x] 条件筛选（sharpe / fitness / turnover 等）
- [x] 属性 PATCH（`patch_properties`）
- [x] 提交前 check（单条 / 并发）
- [x] submit
- [x] 基础 SC（本地，`sc_check` / `sc_check_batch`，OS 池批量只 sync 一次）
- [x] PPAC 本地检测（`ppac_check` / `ppac_check_batch`，参照池为 Power Pool OS alpha）
- [x] 基础 PC（平台 `/correlations/prod`）
- [x] PnL 获取（`GET .../recordsets/pnl`）
- [x] yearly-stats 获取（`GET .../recordsets/yearly-stats`）

# 四、wqb — 模拟

- [x] 单条 simulate
- [x] multisim（`multi_simulate`）
- [x] 并发 simulate（`concurrent_simulate`）
- [x] `build_regular_alpha` 快速组 payload

# 五、wqb — SPC

- [x] SPC zero / submit / deploy

# 六、wqb — 辅助

- [x] `FilterRange` / `DatetimeRange`
- [x] `wait_get`（Retry-After / 空 body / 401 / 429 重试，recordset 等 GET 共用）

# 七、tools — 表达式

- [x] 单条表达式校验（`validate_expression`）
- [x] 批量表达式校验（`validate_expression_batch`）
- [x] 批量校验 JSON 汇总（`validate_expression_batch_json`）
- [x] 算子 / 字段统计（`analyze_expression`）
- [x] 唯一算子计数（`count_unique_operators`）
- [x] 唯一字段计数（`count_unique_fields`）
- [x] ts 窗口槽位提取（`extract_window_slots`）
- [x] ts 窗口回填（`apply_window_values`）
- [x] AST 还原表达式（`program_to_expression`）

# 八、tools — 相关性

- [x] 两个 alpha 近 N 年 PnL 相关（`corr_between_alphas`）
- [x] 两份 PnL 近 N 年相关（`corr_between_pnls`）
- [x] alpha 序列相关矩阵（`corr_matrix_alphas`）
- [x] PnL 序列相关矩阵（`corr_matrix_pnls`）

# 九、tools — 分析

- [x] 每月各地区提交数量（`monthly_submit_count_by_region_json`）


---

*最后更新：2026-09-04*
