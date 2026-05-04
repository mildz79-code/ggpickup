-- 003_rollback.sql
-- Phase 3: remove shipping_schedule tables added by 003_shipping_schema.sql
-- Order: schedule_stops (FKs schedule_days, delivery_requests, greige_pickup_requests)
--        -> schedule_days -> delivery_requests

IF OBJECT_ID('dbo.schedule_stops', 'U') IS NOT NULL
    DROP TABLE dbo.schedule_stops;
GO

IF OBJECT_ID('dbo.schedule_days', 'U') IS NOT NULL
    DROP TABLE dbo.schedule_days;
GO

IF OBJECT_ID('dbo.delivery_requests', 'U') IS NOT NULL
    DROP TABLE dbo.delivery_requests;
GO

PRINT 'Phase 3 shipping schema rollback applied (schedule_stops, schedule_days, delivery_requests dropped if present).';
