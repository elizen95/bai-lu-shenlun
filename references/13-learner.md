# 学习档案与薄弱点训练

## 保存位置与真实记录

用户学习记录放在本skill的 `state/learner.json`，知识规则放在references，课程原文放在数据库。每次学习先读档案，结束时保存实际发生的事件。更新skill时保留已有state。

档案初始仅记录用户指定的教学主线和文字稿偏好。考试、成绩、日期与基础未知时留空。不能把课程案例中的考生分数记成用户成绩，也不能写入不存在的作答或复测。

`scripts/learner.py` 提供read、profile、record操作，更新使用JSON文件参数并原子写入，event_id用于防止重试重复记账。可通过 `--state` 指定隔离测试路径。

```text
python scripts/learner.py read
python scripts/learner.py profile --file work/profile-update.json
python scripts/learner.py record --file work/practice-event.json
```

## 事件内容

发题记录kind为assigned，保留question_id、材料或同题标识、训练目标和日期。作答记录kind为attempt或retest，必须保存学员真实answer、mode，以及有证据的errors。mode区分independent、guided、rewrite、transfer和retest。

可追加实际用时、字数、评分依据、估分区间、材料依据、修改目标、下一次复测日期和原题关联。学员要求不保存某些内容时遵照要求，仍可在当前对话完成教学。保存失败时给出可续接的学习摘要，不宣称已经记住。

下例为字段形状，示例答案不可作为真实学习事件写入。

```json
{
  "event_id": "actual-session-question-attempt-id",
  "kind": "attempt",
  "question_id": "Q-C02-019-1",
  "mode": "independent",
  "answer": "此处由学员真实原答替换",
  "duration_minutes": null,
  "errors": ["E1"],
  "evidence": [{"code": "E1", "answer_quote": "真实句子", "reason": "主体与题干不符"}],
  "score_basis": "C02-018课程标准",
  "next_action": "只重写以小冯为主体的第一条"
}
```

## 如何确定薄弱点

先有作答证据，再归到E1—E16。单题问题记为待观察，在不同题的独立作答中再次出现可记为复发。同一题多次改写不重复计算为多道错题。近期样本少时如实表达置信度，不能只凭某次字数或措辞给学员贴标签。

## 针对性闭环

1. 选择影响最大的上游问题。主体错误先练审题，不能只润色句子。
2. 回到一段真实材料解释原因，做一个最小示范。
3. 让学员自己重写原答的相关部分。
4. 换一道未见材料检验相同能力，不在题目中泄露目标答案。
5. 在后续学习日安排延迟复测。可用约2天与7天作为起点，根据用户节奏调整，明确这是教练设计。
6. 连续异题独立表现稳定后把弱项标为已改善，仍保留历史证据。尚未复测则保持待验证。

## 题目曝光与学习报告

题干、完整材料、参考答案、教师提示分别记录已见情况。内容相同但课程不同的题仍属于复习，选题时核对family、材料主题与原题标识。数据库family只能识别部分精确重复，不能替代语义核题。

报告包含已完成单元、独立作答数量与用时、最近常见问题、已验证改善、待复测任务和下一步。学员要求继续学习时，优先接续未完成任务，不重新进行全套初诊。
