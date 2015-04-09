--
-- Merge Paraflu 1, 2 and 3 counts into "Paraflu"
--
BEGIN;
INSERT INTO lab_diags (report_id, test, diagnosis, count) 
    SELECT report_id, test, 'Paraflu', sum(count) 
        FROM lab_diags 
            WHERE diagnosis LIKE 'Paraflu_' 
            GROUP BY report_id, test;
COMMIT;
