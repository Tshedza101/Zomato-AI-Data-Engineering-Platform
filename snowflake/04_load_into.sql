-- ==============================================================================
-- Phase 2 · Step 5 — Load RAW from S3 (Path 1 batch)
-- Loads the plain CSVs you uploaded to each raw/<table>/ folder. The header
-- row is skipped by the file format (SKIP_HEADER=1), and rows load by position.
-- ==============================================================================

USE ROLE ACCOUNTADMIN;
USE DATABASE ZOMATO;
USE SCHEMA RAW;
USE WAREHOUSE ZOMATO_WH;

-- Fix: CSV fields are enclosed in double-quotes, not single-quotes
ALTER FILE FORMAT CSV_FMT SET FIELD_OPTIONALLY_ENCLOSED_BY = '"';

-- Dimensions = messy rel source data -> tolerate and skip bad rwos (CONTINUE)

COPY INTO RAW.restuarants FROM @ZOMATO_RAW_STAGE/restuarants/   ON_ERROR = 'CONTINUE';
COPY INTO RAW.users       FROM @ZOMATO_RAW_STAGE/users/         ON_ERROR = 'CONTINUE';
COPY INTO RAW.food       FROM @ZOMATO_RAW_STAGE/food/           ON_ERROR = 'CONTINUE';
COPY INTO RAW.menu       FROM @ZOMATO_RAW_STAGE/menu/           ON_ERROR = 'CONTINUE';

-- Facts = clean generated data -> stay strict so counts are exact.
COPY INTO RAW.orders      FROM @ZOMATO_RAW_STAGE/orders/       ON_ERROR = 'ABORT_STATEMENT';
COPY INTO RAW.order_items FROM @ZOMATO_RAW_STAGE/order_items/  ON_ERROR = 'ABORT_STATEMENT';
COPY INTO RAW.reviews     FROM @ZOMATO_RAW_STAGE/reviews/      ON_ERROR = 'ABORT_STATEMENT';

-- Sanity check.
SELECT 'restuarants' t, COUNT(*) n FROM RAW.restuarants
UNION ALL SELECT 'users',       COUNT(*) FROM RAW.users
UNION ALL SELECT 'food',        COUNT(*) FROM RAW.food
UNION ALL SELECT 'menu',        COUNT(*) FROM RAW.menu
UNION ALL SELECT 'orders',      COUNT(*) FROM RAW.orders
UNION ALL SELECT 'order_items', COUNT(*) FROM RAW.order_items
UNION ALL SELECT 'reviews',     COUNT(*) FROM RAW.reviews
ORDER BY t; 
-- Expect: orders = 10,000,000 · order_items ≈ 23,000,000 · restaurants ≈ 148,541 ...

DESCRIBE TABLE ZOMATO.RAW.ORDERS;

DESCRIBE TABLE ZOMATO.RAW.MENU;




