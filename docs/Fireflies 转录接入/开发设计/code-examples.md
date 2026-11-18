# Fireflies 会议转录接入 — 代码示例

> 关联文档: [开发设计](./dev-design-doc.md) · [设计](../设计/design-doc.md)
>
> DDL 以仓库里的迁移文件为准（表的字段说明、索引用途见开发设计第 1 节）；本文只列迁移文件与提取输入的示例。

## 1. Java 迁移 `deploy/upgrade_doc/sprint122/V1__ff_init.sql`

路径相对 `java/CIOaas-api/`：

- `deploy/upgrade_doc/sprint122/V1__ff_init.sql`：建 J1~J6（`ff_connection_configuration` / `ff_meeting_meta_info` / `ff_meeting_sentence` / `ff_cheat_sheet` / `ff_expertise_tag` / `ff_expert_rejection`）及索引、注释，存量组织补齐预置专长标签；先于 Java 与 Python 发版执行，可重跑。
- `deploy/upgrade_doc/sprint122/V4__ff_cheat_sheet_seed.sql`：Golden Section 租户的名册初始数据写入 `ff_cheat_sheet`；V1 之后执行，发版前后均可，可重跑。

## 2. Python 迁移 `sql/migrations/business/V034__sprint122_fireflies_init.sql`

路径相对 `python/CIOaas-python/`：

- `sql/migrations/business/V034__sprint122_fireflies_init.sql`：建 `ai_ff_*`（P1~P5、P7、P8）及索引、注释、共用的 `updated_at` 触发器函数；X1 `ai_file_registry` 与 `ai_rag_business_association` 的 `business_type` 注释补新取值；`ai_rag_entry` 加 `file_id` 索引；定时清扫扫描用的部分索引。先于 Python 与 Java 发版执行，可重跑。
- `sql/migrations/business/V035__sprint122_fireflies_routing_row_tab_index_anon.sql`：`idx_ai_ff_routing_row_tab` 纳入 `TESTIMONY_ANON`（公司端 Expert Testimony 页签列匿名版）；发版前后均可，可重跑。

## 3. 提取输入（`current_extraction_input`）示例

只存提取时用的页头输入，不存提取出的内容；键为 camelCase（`ExtractionInputDTO` 的 `model_dump(by_alias=True)`）。

```json
{
  "meetingType": "GS_FOUNDER",
  "companyIds": ["c-techvision"],
  "participants": [
    {"id": "p1", "role": "FOUNDER", "organization": "TechVision Inc.", "companyId": "c-techvision", "expertiseTags": []},
    {"id": "p2", "role": "UNIDENTIFIED", "organization": null, "companyId": null, "expertiseTags": []}
  ],
  "speakers": [
    {"speakerId": 0, "participantId": "p1"},
    {"speakerId": 1, "participantId": null}
  ]
}
```

含义：这版内容按「GS → 创始人、公司 TechVision、p2 未识别、1 号说话人没对上」提取。之后管理员把 p2 登记为 LP，最新识别结果与它不一致，即「参会人有改动」。

## 4. 定时清扫要接手的会议（供清扫功能设计参考）

已由定时清扫接手，扫描条件、时限与收尾动作（含补投发送失败后人工把 `redispatched_at` 置空、下一轮清扫再补投一次）见 [卡死任务清扫](../../卡死任务清扫/开发设计/dev-design-doc.md) 第 4 节，清扫没跑时的人工应急见其 4.8。
