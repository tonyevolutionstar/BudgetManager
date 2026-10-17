DROP TABLE IF EXISTS Transfer;
DROP TABLE IF EXISTS MLTrainingSample;
DROP TABLE IF EXISTS Budget;
DROP TABLE IF EXISTS BankStatementExportFormat;
DROP TABLE IF EXISTS ClassificationRule;
DROP TABLE IF EXISTS BankTransaction;
DROP TABLE IF EXISTS Account;
DROP TABLE IF EXISTS Bank;
DROP TABLE IF EXISTS AccountType;
DROP TABLE IF EXISTS SubCategory;
DROP TABLE IF EXISTS Category;
DROP TABLE IF EXISTS CategoryType;

CREATE TABLE IF NOT EXISTS AccountType (
  ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  NAME VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO AccountType (NAME)
VALUES ('Checking'), ('Savings'), ('Money Market');

CREATE TABLE IF NOT EXISTS CategoryType (
  ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  NAME VARCHAR(20) NOT NULL UNIQUE
);

INSERT INTO CategoryType(NAME)
VALUES ('EXPENSE'), ('INCOME'), ('TRANSFER');

CREATE TABLE IF NOT EXISTS Category (
  ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  NAME VARCHAR(100) NOT NULL UNIQUE,
  CategoryTypeId INT NOT NULL REFERENCES CategoryType(Id),
  Color CHAR(7),
  Icon VARCHAR(10),
  MonthlyBudget NUMERIC(10, 2) NOT NULL
);

INSERT INTO Category (Name, CategoryTypeId, Color, Icon, MonthlyBudget)
SELECT v.name, ct.id, v.color, v.icon, v.budget
FROM (VALUES
  ('Housing',       'EXPENSE', '#0000FF', '🏠', 1000.0),
  ('Transportation','EXPENSE', '#00FF00', '🚗',  500.0),
  ('Food',          'EXPENSE', '#FFA500', '🍔',  300.0),
  ('Utilities',     'EXPENSE', '#800080', '💡',  200.0),
  ('Entertainment', 'EXPENSE', '#FF0000', '🎉',  150.0),
  ('Healthcare',    'EXPENSE', '#FFC0CB', '💊',  200.0),
  ('Insurance',     'EXPENSE', '#00FFFF', '🛡️',  300.0),
  ('Personal',      'EXPENSE', '#FF00FF', '👤',  100.0),
  ('Debt',          'EXPENSE', '#A52A2A', '💳',  400.0),
  ('Savings',       'EXPENSE', '#008080', '💰',  500.0),
  ('Gifts',         'EXPENSE', '#FFFF00', '🎁',  100.0),
  ('Education',     'EXPENSE', '#808080', '📚',  400.0),
  ('Income',        'INCOME',  '#000000', '💼',    0.0),
  ('Subscriptions', 'EXPENSE', '#4B0082', '📱',   50.0),
  ('Others',        'EXPENSE', '#D3D3D3', '❓',  250.0)
) AS v(name, type_name, color, icon, budget)
JOIN CategoryType ct ON ct.name = v.type_name;

CREATE TABLE IF NOT EXISTS SubCategory (
  ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  categoryId INT NOT NULL,
  CONSTRAINT fk_category
  FOREIGN KEY (categoryId) REFERENCES category(ID), 
  UNIQUE (NAME, categoryId)
);

INSERT INTO SubCategory (Name, CategoryId)
SELECT v.name, c.id
FROM (VALUES
  ('Rent', 'Housing'), ('Credit', 'Housing'), ('Condominium', 'Housing'),
  ('Electricity and Gas', 'Housing'), ('Water', 'Housing'), ('Internet', 'Housing'),
  ('Public Transport', 'Transportation'), ('Fuel', 'Transportation'), ('Car Inspection', 'Transportation'),
  ('Car MaINTenance', 'Transportation'), ('Parking fee', 'Transportation'),
  ('Groceries', 'Food'), ('Restaurants', 'Food'), ('Coffee Shop', 'Food'), ('Bakery', 'Food'),
  ('Phone', 'Utilities'),
  ('Movies', 'Entertainment'), ('Concerts', 'Entertainment'), ('Games', 'Entertainment'),
  ('Dentist', 'Healthcare'), ('Hospital', 'Healthcare'), ('Pharmacy', 'Healthcare'),
  ('Psychiatrist', 'Healthcare'), ('Exams', 'Healthcare'),
  ('Health', 'Insurance'), ('House', 'Insurance'),
  ('Gym', 'Personal'), ('Haircut', 'Personal'), ('Clothing', 'Personal'), ('Shoes', 'Personal'),
  ('Credit Cards', 'Debt'),
  ('House', 'Savings'),
  ('Birthday', 'Gifts'), ('Wedding', 'Gifts'),
  ('Birthday', 'Income'), ('Holidays', 'Income'), ('Salary', 'Income'),
  ('Spotify', 'Subscriptions'), ('Apple', 'Subscriptions'), ('Netflix', 'Subscriptions'),
  ('Disney', 'Subscriptions'), ('Prime', 'Subscriptions'), ('HBO', 'Subscriptions'),
  ('Youtube Premium', 'Subscriptions')
) AS v(name, category_name)
JOIN Category c ON c.name = v.category_name;

CREATE INDEX IF NOT EXISTS idx_subcategory_category ON SubCategory (categoryId);

CREATE TABLE IF NOT EXISTS ClassificationRule (
  ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, 
  Pattern VARCHAR(200) NOT NULL,
  MatchType VARCHAR(10) NOT NULL, 
  CategoryId INT NOT NULL REFERENCES CATEGORY(Id),
  SubCategoryId INT NULL REFERENCES SubCategory(Id)
);

CREATE INDEX idx_rule_pattern on ClassificationRule (LOWER(pattern));

CREATE TABLE IF NOT EXISTS Bank (
  ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  NAME TEXT NOT NULL,
  Abbreviation TEXT NOT NULL,
  DatePattern TEXT NOT NULL,
  DateEncoding TEXT NOT NULL
);

INSERT INTO Bank (Name, Abbreviation, DatePattern, DateEncoding)
VALUES
  ('Caixa Geral Depósitos', 'CGD',       '(\d{2}[/-]\d{2}[/-]\d{4})', 'latin1'),
  ('Millennium BCP',        'BCP',       '(\d{4}[/-]\d{2}[/-]\d{2})', 'utf-8'),
  ('Novo Banco',            'NB',        '(\d{2}[/-]\d{2}[/-]\d{4})', 'utf-8'),
  ('Santander',             'Santander', '(\d{2}[/-]\d{2}[/-]\d{4})', 'latin1'),
  ('Banco BPI',             'BPI',       '(\d{2}[/-]\d{2}[/-]\d{4})', 'utf-8');

CREATE TABLE IF NOT EXISTS Account (
  ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  NAME VARCHAR(20) NOT NULL UNIQUE,
  Iban VARCHAR(34) NOT NULL UNIQUE, 
  BankId INT NOT NULL REFERENCES Bank(Id), 
  Currency CHAR(3) NOT NULL, 
  AccountTypeId INT NOT NULL REFERENCES AccountType(ID),
  CurrentBalance NUMERIC(14, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS BankTransaction (
  ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  AccountId INT NOT NULL REFERENCES Account(Id), 
  OperationDate DATE NOT NULL,
  ValueDate Date, 
  Description Text NOT NULL,
  Amount NUMERIC(14, 2) NOT NULL,
  AccountingBalance NUMERIC(14, 2) NOT NULL,
  CategoryId INT NOT NULL REFERENCES CATEGORY(Id),
  SubCategoryId INT NULL REFERENCES SubCategory(Id)
);

CREATE INDEX IF NOT EXISTS  idx_tx_account_date ON BankTransaction (accountid, operationdate DESC);
CREATE INDEX IF NOT EXISTS idx_tx_category      ON BankTransaction (categoryid);
CREATE INDEX IF NOT EXISTS idx_tx_date          ON BankTransaction (operationdate DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_tx_dedupe  ON BankTransaction (AccountId, OperationDate, Amount, AccountingBalance, md5(Description));

CREATE TABLE IF NOT EXISTS BankStatementExportFormat (
	ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	ColumnsExport TEXT NOT NULL,
	BankId INT NOT NULL REFERENCES Bank(Id),
  CONSTRAINT uq_export_format UNIQUE (BankId, ColumnsExport)
);

INSERT INTO BankStatementExportFormat (ColumnsExport, BankId)
VALUES 
	('Date;BalanceDate;Description;Expense;Income;Accounting Balance;Balance;Category', 1);

CREATE TABLE IF NOT EXISTS Budget (
  ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  CategoryId INT NOT NULL REFERENCES Category(Id), 
  Year SMALLINT NOT NULL, 
  Month SMALLINT NOT NULL, 
  Amount NUMERIC (10, 2) NOT NULL, 
  Unique (CategoryId, YEAR, MONTH)
);

CREATE TABLE IF NOT EXISTS Transfer (
    id              INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fromAccountId   INTEGER  NOT NULL REFERENCES Account(id),
    toAccountId     INTEGER  NOT NULL REFERENCES Account(id),
    amount          NUMERIC(14,2) NOT NULL,
    transferDate    DATE NOT NULL,
    description     TEXT,
    fromBankTxId    INTEGER  REFERENCES BankTransaction(id),
    toBankTxId      INTEGER  REFERENCES BankTransaction(id),
    CHECK (fromAccountId <> toAccountId)
);

CREATE TABLE IF NOT EXISTS MLTrainingSample (
    id              INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    description     TEXT    NOT NULL,
    categoryId      INTEGER NOT NULL REFERENCES Category(id),
    subCategoryId   INTEGER REFERENCES SubCategory(id),
    source          VARCHAR(20) DEFAULT 'manual'
                    CHECK (source IN ('manual','confirmed_ml','confirmed_rule')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ml_subcategory
    FOREIGN KEY (sub_category_id, category_id) REFERENCES SubCategory (ID, categoryId)
);
 
CREATE INDEX IF NOT EXISTS idx_ml_category ON MLTrainingSample (categoryId);

DELETE FROM MLTrainingSample a
USING MLTrainingSample b
WHERE a.id < b.id
  AND a.categoryid = b.categoryid
  AND md5(lower(a.description)) = md5(lower(b.description));
 
CREATE UNIQUE INDEX IF NOT EXISTS uq_ml_sample ON MLTrainingSample (md5(lower(description)), categoryid);