USE ROLE ACCOUNTADMIN;
USE DATABASE ZOMATO;
USE SCHEMA RAW;

-- Plain CSV (manual upload, no gzip). Files KEEP their header row -> SKIP_HEADER = 1.
-- Comment fields (reviews) contain commas but are quoted, so keep the quote char.

CREATE OR REPLACE FILE FORMAT ZOMATO.RAW.CSV_FMT
    TYPE = 'CSV'
    COMPRESSION = 'AUTO'                         -- plain CSV
    FIELD_DELIMITER = ','
    FIELD_OPTIONALLY_ENCLOSED_BY = ''''
    SKIP_HEADER = 1                             -- skip the header row your CSVs still have
    EMPTY_FIELD_AS_NULL = TRUE
    NULL_IF = ('', '\\N', 'NULL')
    TRIM_SPACE = FALSE
    ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE;  -- messy source rows (e.g. food.csv missing a
                                             -- trailing field) NULL-fill instead of aborting

-- 2. Create Internal Snowflake Stage (Replaces AWS S3)
CREATE OR REPLACE STAGE ZOMATO.RAW.ZOMATO_RAW_STAGE
    FILE_FORMAT = ZOMATO.RAW.CSV_FMT; 
    
-- Verify if files are uploaded successfully   
LIST @ZOMATO.RAW.ZOMATO_RAW_STAGE;
