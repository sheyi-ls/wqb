# wqb 能力清单

> **wqb** = 纯 BRAIN HTTP SDK · **tools** = 工具包（依赖 wqb，不发 HTTP）  
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

# 七、tools — 表达式（``wqb/tools/expr``，与 ``wqb/wqb`` SDK 包同级）

- [x] 表达式验证（``validate_expression`` / ``validate_expression_batch`` / ``validate_expression_batch_json``，免查名单 + wqb 字段 API，无 CSV；parse 暂 bridge ``kits/validate_expression``）
- [x] 唯一算子 / 字段计数（``analyze_expression``）
- [x] ts 窗口槽位提取 / 回填（``extract_window_slots`` / ``apply_window_values``）

# 八、tools — 相关性 / 检查

- [x] 候选 PnL 相关矩阵（``tools.correlation.pnl_corr_matrix_json``，PnL 走 wqb ``get_pnl``）


# 九、tools — 分析

- [x] 每月各地区提交数量（``tools.analysis.monthly_submit_count_by_region_json``）


---

*最后更新：2026-09-01*
