CREATE TABLE [brokerCredentials] (
  [id] INT IDENTITY(1, 1) PRIMARY KEY,
  [brokerName] INTEGER NOT NULL,
  [credentials] NVARCHAR(MAX) NOT NULL,
  [createdAt] DATETIME NOT NULL DEFAULT GETDATE(),
  [updatedAt] DATETIME NOT NULL DEFAULT GETDATE()
);

CREATE TYPE [brokerCredentialsType] AS TABLE (
  [id] INT,
  [brokerName] INTEGER,
  [credentials] NVARCHAR(MAX),
  [createdAt] DATETIME ,
  [updatedAt] DATETIME 
);
