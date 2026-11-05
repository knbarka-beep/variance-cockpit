-- 11_v_comments.sql
-- WHAT: Every material variance with its AI draft comment and the controller's review
--       side by side, for the dashboard.
-- HOW:  1. Load the AI drafts (data/ai/drafts.json, written by draft_comments.py) and the
--          reviews (data/ai/reviews.csv, filled in by the controller) as tables.
--          The draft's output and figure check are nested JSON objects (STRUCTs);
--          dot notation (d.output.comment) reads a field inside them.
--       2. LEFT JOIN both onto v_material_variances by variance_id, so a variance without
--          a draft or review yet still appears, with NULLs.
--       3. NULLIF(x, '') turns an empty review cell into NULL ("not reviewed yet").

CREATE OR REPLACE TABLE ai_drafts AS
SELECT * FROM read_json('data/ai/drafts.json', format = 'array', columns = {
    'variance_id': 'VARCHAR', 'input_hash': 'VARCHAR', 'model': 'VARCHAR', 'prompt_version': 'VARCHAR', 'created_at': 'VARCHAR',  -- kept as ISO text, e.g. 2026-11-01T20:41:07+00:00
    'output': 'STRUCT(comment VARCHAR, cause_category VARCHAR, persistence VARCHAR,
                      figures_cited DOUBLE[], no_clear_cause BOOLEAN)',
    'figure_check': 'STRUCT(figures_found INTEGER, figures_matched INTEGER, unmatched VARCHAR[],
                            check_passed BOOLEAN, word_count INTEGER)'});

CREATE OR REPLACE TABLE ai_reviews AS
SELECT * FROM read_csv('data/ai/reviews.csv', header = true, all_varchar = true, columns = {
    'variance_id': 'VARCHAR', 'status': 'VARCHAR', 'final_comment': 'VARCHAR', 'reviewer_note': 'VARCHAR', 'reviewed_by': 'VARCHAR'});

CREATE OR REPLACE VIEW v_comments AS
SELECT
    m.variance_id,
    m.period,
    m.rank_in_month,
    m.variance_type,
    m.account_no,
    m.account_name,
    m.cost_centre,
    m.variance_profit_dkk,
    m.variance_pct,
    d.output.comment                AS ai_comment,
    d.output.cause_category         AS ai_cause_category,
    d.output.persistence            AS ai_persistence,
    d.output.no_clear_cause         AS ai_no_clear_cause,
    d.figure_check.check_passed     AS figure_check_passed,
    d.figure_check.unmatched        AS figure_check_unmatched,
    d.model                         AS ai_model,
    d.prompt_version                AS ai_prompt_version,
    d.created_at                    AS ai_created_at,
    NULLIF(r.status, '')            AS review_status,
    NULLIF(r.final_comment, '')     AS final_comment,
    NULLIF(r.reviewer_note, '')     AS reviewer_note,
    NULLIF(r.reviewed_by, '')       AS reviewed_by      -- claude = Claude's suggested status; knut = checked by Knut
FROM v_material_variances m
LEFT JOIN ai_drafts d  ON d.variance_id = m.variance_id
LEFT JOIN ai_reviews r ON r.variance_id = m.variance_id;
