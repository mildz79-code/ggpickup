-- 004_dyeserver_sync_log.sql
-- Phase 4: Dyeserver sync audit log.
-- Target: SQL Server 2008 R2 on IDSERVER, database `ggpickup`.

IF OBJECT_ID('dbo.dyeserver_sync_log', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.dyeserver_sync_log (
        id          INT IDENTITY(1,1) PRIMARY KEY,
        run_at      DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
        pulled      INT          NOT NULL DEFAULT 0,
        inserted    INT          NOT NULL DEFAULT 0,
        updated     INT          NOT NULL DEFAULT 0,
        errors      INT          NOT NULL DEFAULT 0,
        error_text  NVARCHAR(MAX) NULL
    );
    CREATE INDEX ix_sync_log_run_at ON dbo.dyeserver_sync_log(run_at DESC);
END;
GO

PRINT 'Phase 4 sync log schema applied.';
