-- 003_seed_test.sql
-- Inserts three sample dbo.delivery_requests rows for TODAY (CAST(GETDATE() AS DATE)).
-- Uses the first three active ship_to_locations.codes by ROW_NUMBER — no fabricated codes.
-- Remove before trusting production counts: DELETE FROM dbo.delivery_requests WHERE notes LIKE N'SEED TEST DATA %';

DECLARE @today DATE;
SET @today = CAST(GETDATE() AS DATE);

DECLARE @code1 VARCHAR(10);
DECLARE @code2 VARCHAR(10);
DECLARE @code3 VARCHAR(10);

SET @code1 = NULL;
SET @code2 = NULL;
SET @code3 = NULL;

;WITH ranked AS (
    SELECT
        code,
        ROW_NUMBER() OVER (ORDER BY code) AS rn
    FROM dbo.ship_to_locations
    WHERE is_active = 1
)
SELECT @code1 = (SELECT TOP 1 code FROM ranked WHERE rn = 1),
       @code2 = (SELECT TOP 1 code FROM ranked WHERE rn = 2),
       @code3 = (SELECT TOP 1 code FROM ranked WHERE rn = 3);

IF @code1 IS NULL OR @code2 IS NULL OR @code3 IS NULL
BEGIN
    RAISERROR ('ship_to_locations must have at least three active rows (is_active = 1) for seeding.', 16, 1);
    RETURN;
END

-- Pending
INSERT INTO dbo.delivery_requests (request_date, customer_code, lot_number, qty, status, source, delivered_at, delivered_by, lat, lng, notes) VALUES (@today, @code1, N'SEED-LOT-PENDING', 1, N'Pending', N'manual', NULL, NULL, NULL, NULL, N'SEED TEST DATA - DELETE BEFORE PRODUCTION USE');
-- Delivered
INSERT INTO dbo.delivery_requests (request_date, customer_code, lot_number, qty, status, source, delivered_at, delivered_by, lat, lng, notes) VALUES (@today, @code2, N'SEED-LOT-DELIVERED', 1, N'Delivered', N'manual', CAST(GETDATE() AS DATETIME2(3)), NULL, NULL, NULL, N'SEED TEST DATA - DELETE BEFORE PRODUCTION USE');
-- Cancelled
INSERT INTO dbo.delivery_requests (request_date, customer_code, lot_number, qty, status, source, delivered_at, delivered_by, lat, lng, notes) VALUES (@today, @code3, N'SEED-LOT-CANCELLED', 1, N'Cancelled', N'manual', NULL, NULL, NULL, NULL, N'SEED TEST DATA - DELETE BEFORE PRODUCTION USE');

PRINT 'Inserted 003 seed rows into delivery_requests — remove with DELETE ... WHERE notes LIKE N''SEED TEST DATA %''.';
