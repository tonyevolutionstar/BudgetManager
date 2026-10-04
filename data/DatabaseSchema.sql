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
  CategoryTypeId INT NOT NULL references CategoryType(Id),
  color char(7),
  icon VARCHAR(10),
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
  ID int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name varchar(200) not null,
  categoryId int not null,
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
  ('Car Maintenance', 'Transportation'), ('Parking fee', 'Transportation'),
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

CREATE TABLE IF NOT EXISTS ClassificationRule (
  ID int GENERATED ALWAYS AS IDENTITY PRIMARY KEY, 
  Pattern varchar(200) NOT NULL,
  MatchType varchar(10) NOT NULL DEFAULT 'contains' CHECK (MatchType IN ('contains', 'starts_with', 'exact', 'regex')), 
  CategoryId int NOT NULL REFERENCES CATEGORY(Id),
  SubCategoryId int NULL REFERENCES SubCategory(Id)
);

CREATE INDEX idx_rule_pattern on ClassificationRule (LOWER(pattern));

CREATE TABLE IF NOT EXISTS Bank (
  ID int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  NAME text not null,
  Abbreviation text not null,
  DatePattern text not null,
  DateEncoding text not null
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
  Iban varchar(34) NOT NULL UNIQUE, 
  BankId int not null references Bank(Id), 
  Currency char(3) NOT NULL, 
  AccountTypeId int not null references AccountType(ID),
  CurrentBalance numeric(14, 2) not null
);

CREATE TABLE IF NOT EXISTS BankTransaction (
  ID int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  AccountId int not null References Account(Id), 
  OperationDate DATE not null,
  ValueDate Date, 
  Description Text not null,
  Amount numeric(14, 2) not null,
  AccountingBalance numeric(14, 2) not null,
  CategoryId int not null REFERENCES CATEGORY(Id),
  SubCategoryId int null References SubCategory(Id).
    CONSTRAINT fk_tx_subcategory
    FOREIGN KEY (SubCategoryId, CategoryId) REFERENCES SubCategory (ID, categoryId)
);

CREATE INDEX idx_tx_account_date ON BankTransaction (accountid, operationdate DESC);
CREATE INDEX idx_tx_category     ON BankTransaction (categoryid);
CREATE INDEX idx_tx_date         ON BankTransaction (operationdate DESC);

CREATE TABLE IF NOT EXISTS BankStatementExportFormat (
	ID int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	ColumnsExport text not null,
	BankId int not null references Bank(Id)
);

INSERT INTO BankStatementExportFormat (ColumnsExport, BankId)
VALUES 
	('Date;BalanceDate;Description;Expense;Income;Accounting Balance;Balance;Category', 1);

CREATE TABLE IF NOT EXISTS Budget (
  ID int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  CategoryId int NOT NULL REFERENCES Category(Id), 
  Year smallint NOT NULL, 
  MONTH SMALLINT NOT NULL, 
  Amount numeric (10, 2) NOT NULL, 
  Unique (CategoryId, YEAR, MONTH)
);

CREATE TABLE IF NOT EXISTS Transfer (
    id              SERIAL PRIMARY KEY,
    fromAccountId   INTEGER      NOT NULL REFERENCES Account(id),
    toAccountId     INTEGER      NOT NULL REFERENCES Account(id),
    amount          NUMERIC(14,2) NOT NULL,
    transferDate    DATE         NOT NULL,
    description     TEXT,
    fromBankTxId    INTEGER      REFERENCES BankTransaction(id),
    toBankTxId     INTEGER      REFERENCES BankTransaction(id)
);

CREATE TABLE IF NOT EXISTS MLTrainingSample (
    id              SERIAL PRIMARY KEY,
    description     TEXT    NOT NULL,
    categoryId      INTEGER NOT NULL REFERENCES Category(id),
    subCategoryId   INTEGER REFERENCES SubCategory(id),
    source          VARCHAR(20) DEFAULT 'manual' CHECK (source IN ('manual','confirmed_ml','confirmed_rule')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
 
CREATE INDEX idx_ml_category ON MLTrainingSample (categoryId);

CREATE UNIQUE INDEX IF NOT EXISTS uq_tx_dedupe
  ON BankTransaction (AccountId, OperationDate, Amount, AccountingBalance, md5(Description));