-- 
--  The contents of this file are subject to the HACOS License Version 1.2
--  (the "License"); you may not use this file except in compliance with
--  the License.  Software distributed under the License is distributed
--  on an "AS IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
--  implied. See the LICENSE file for the specific language governing
--  rights and limitations under the License.  The Original Software
--  is "NetEpi Collection". The Initial Developer of the Original
--  Software is the Health Administration Corporation, incorporated in
--  the State of New South Wales, Australia.
-- 
--  Copyright (C) 2004-2011 Health Administration Corporation and others. 
--  All Rights Reserved.
-- 
--  Contributors: See the CONTRIBUTORS file for details of contributions.
-- 

BEGIN;

-- Overview - per lab per week
CREATE TABLE lab_reports (
    report_id SERIAL UNIQUE PRIMARY KEY,
    lab VARCHAR,
    week TIMESTAMP,
    notes VARCHAR,
    completed TIMESTAMP
);

CREATE INDEX lr_l_idx
    ON lab_reports (lab);

CREATE UNIQUE INDEX lr_lw_idx
    ON lab_reports (lab,week);

-- Total tests performed - per lab per week per test
CREATE TABLE lab_totals (
    report_id INTEGER REFERENCES lab_reports ON DELETE CASCADE,
    test VARCHAR,
    count INTEGER
);

CREATE INDEX lt_r_idx
    ON lab_totals (report_id);

CREATE UNIQUE INDEX lt_rt_idx
    ON lab_totals (report_id,test);


-- Positive diagnoses - per lab per week per test per diagnosis
CREATE TABLE lab_diags (
    report_id INTEGER REFERENCES lab_reports ON DELETE CASCADE,
    test VARCHAR,
    diagnosis VARCHAR,
    count INTEGER
);

CREATE INDEX ld_r_idx
    ON lab_diags (report_id);

CREATE UNIQUE INDEX ld_rtd_idx
    ON lab_diags (report_id,test,diagnosis);

-- Postive case details
CREATE TABLE lab_cases (
    report_id INTEGER REFERENCES lab_reports ON DELETE CASCADE,
    idx INTEGER,
    test VARCHAR,
    diagnosis VARCHAR,
    age FLOAT,
    sex VARCHAR,
    suburb VARCHAR,
    postcode VARCHAR
);
CREATE INDEX lc_r_idx
    ON lab_cases (report_id);

CREATE UNIQUE INDEX lc_ri_idx
    ON lab_cases (report_id,idx);

COMMIT;
