-- ================================================================
-- DriveEasy — Buat tabel Reviews
-- Jalankan script ini sekali di SQL Server Management Studio
-- atau tool database Anda
-- ================================================================

IF NOT EXISTS (
    SELECT 1 FROM sys.tables WHERE name = 'Reviews'
)
BEGIN
    CREATE TABLE Reviews (
        id          INT IDENTITY(1,1) PRIMARY KEY,
        name        NVARCHAR(100)  NOT NULL,
        email       NVARCHAR(150)  NULL,
        rating      TINYINT        NOT NULL CHECK (rating BETWEEN 1 AND 5),
        message     NVARCHAR(2000) NOT NULL,
        is_approved BIT            NOT NULL DEFAULT 1,
        created_at  DATETIME       NOT NULL DEFAULT GETDATE()
    );
    PRINT 'Tabel Reviews berhasil dibuat.';
END
ELSE
BEGIN
    PRINT 'Tabel Reviews sudah ada, dilewati.';
END
