-- 003_shipping_schema.sql
-- Phase 3: Shipping Schedule schema.
-- Target: SQL Server 2008 R2 on IDSERVER, database `ggpickup`.
-- Safe to re-run: each CREATE is guarded by OBJECT_ID check.

-- =============================================================================
-- delivery_requests
--   Mirrors greige_pickup_requests shape but for outbound shipments.
--   `source`='manual' during Phase 3; 'dyeserver' populated in Phase 4.
-- =============================================================================
IF OBJECT_ID('dbo.delivery_requests', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.delivery_requests (
        id                INT IDENTITY(1,1) PRIMARY KEY,
        request_date      DATE            NOT NULL,
        customer_code     VARCHAR(10)     NOT NULL,
        lot_number        VARCHAR(200)    NULL,
        qty               INT             NOT NULL DEFAULT 1,
        status            VARCHAR(20)     NOT NULL DEFAULT 'Pending',
        source            VARCHAR(20)     NOT NULL DEFAULT 'manual',
        dyeserver_ref     VARCHAR(100)    NULL,
        delivered_at      DATETIME2(3)    NULL,
        delivered_by      UNIQUEIDENTIFIER NULL,
        lat               DECIMAL(9,6)    NULL,
        lng               DECIMAL(9,6)    NULL,
        notes             NVARCHAR(MAX)   NULL,
        created_at        DATETIME2(3)    NOT NULL DEFAULT SYSUTCDATETIME(),
        CONSTRAINT chk_delivery_status CHECK (status IN ('Pending','Delivered','Cancelled')),
        CONSTRAINT chk_delivery_source CHECK (source IN ('manual','dyeserver'))
    );

    CREATE INDEX ix_delivery_date        ON dbo.delivery_requests(request_date);
    CREATE INDEX ix_delivery_status      ON dbo.delivery_requests(status);
    CREATE UNIQUE INDEX ux_delivery_dyeref
        ON dbo.delivery_requests(dyeserver_ref) WHERE dyeserver_ref IS NOT NULL;
END;
GO

-- =============================================================================
-- schedule_days  — one row per working day
-- =============================================================================
IF OBJECT_ID('dbo.schedule_days', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.schedule_days (
        id             INT IDENTITY(1,1) PRIMARY KEY,
        schedule_date  DATE            NOT NULL UNIQUE,
        created_by     UNIQUEIDENTIFIER NULL,
        notes          NVARCHAR(MAX)   NULL,
        created_at     DATETIME2(3)    NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

-- =============================================================================
-- schedule_stops  — ordered stops referencing either a pickup or a delivery
-- =============================================================================
IF OBJECT_ID('dbo.schedule_stops', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.schedule_stops (
        id                    INT IDENTITY(1,1) PRIMARY KEY,
        schedule_day_id       INT             NOT NULL,
        stop_type             VARCHAR(10)     NOT NULL,
        pickup_request_id     INT             NULL,
        delivery_request_id   INT             NULL,
        sequence              INT             NOT NULL,
        driver_id             UNIQUEIDENTIFIER NULL,
        eta                   DATETIME2(3)    NULL,
        completed_at          DATETIME2(3)    NULL,
        CONSTRAINT fk_stops_day
            FOREIGN KEY (schedule_day_id)     REFERENCES dbo.schedule_days(id),
        CONSTRAINT fk_stops_pickup
            FOREIGN KEY (pickup_request_id)   REFERENCES dbo.greige_pickup_requests(id),
        CONSTRAINT fk_stops_delivery
            FOREIGN KEY (delivery_request_id) REFERENCES dbo.delivery_requests(id),
        CONSTRAINT chk_stops_type     CHECK (stop_type IN ('pickup','delivery')),
        CONSTRAINT chk_stops_ref_xor  CHECK (
            (stop_type = 'pickup'   AND pickup_request_id   IS NOT NULL AND delivery_request_id IS NULL) OR
            (stop_type = 'delivery' AND delivery_request_id IS NOT NULL AND pickup_request_id   IS NULL)
        )
    );
    CREATE INDEX ix_stops_day_seq ON dbo.schedule_stops(schedule_day_id, sequence);
    CREATE INDEX ix_stops_driver  ON dbo.schedule_stops(driver_id);
END;
GO

PRINT 'Phase 3 shipping schema applied.';
