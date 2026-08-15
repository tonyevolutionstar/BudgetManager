DROP TABLE IF EXISTS ClassificationRule;
DROP TABLE IF EXISTS BankTransaction;
DROP TABLE IF EXISTS BankStatementExportFormat;
DROP TABLE IF EXISTS Transfer;
DROP TABLE IF EXISTS Bank;
DROP TABLE IF EXISTS Budget;
DROP TABLE IF EXISTS MLTrainingSample;
DROP TABLE IF EXISTS Account;
DROP TABLE IF EXISTS AccountType;
DROP TABLE IF EXISTS SubCategory;
DROP TABLE IF EXISTS Category;
DROP TABLE IF EXISTS CategoryType;

CREATE TABLE AccountType (
  ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  NAME VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO AccountType (NAME)
VALUES 
  ('Checking'),
  ('Savings'), 
  ('Money Market');

CREATE TABLE CategoryType (
  ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  NAME VARCHAR(20) NOT NULL UNIQUE
);

INSERT INTO CategoryType(NAME)
VALUES 
  ('EXPENSE'),
  ('INCOME'), 
  ('TRANSFER');

CREATE TABLE Category (
  ID int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  NAME varchar(100) NOT NULL UNIQUE,
  CategoryTypeId int NOT NULL references CategoryType(Id),
  color char(7),
  icon varchar(10),
  MonthlyBudget NUMERIC(10, 2) NOT NULL
);

INSERT INTO Category (Name, CategoryTypeId, Color, Icon, MonthlyBudget)
VALUES 
  ('Housing', 1, '#0000FF', '🏠', 1000.0),
  ('Transportation', 1, '#00FF00', '🚗', 500.0),
  ('Food', 1, '#FFA500', '🍔', 300.0),
  ('Utilities', 1, '#800080', '💡', 200.0),
  ('Entertainment', 1, '#FF0000', '🎉', 150.0),
  ('Healthcare', 1, '#FFC0CB', '💊', 200.0),
  ('Insurance', 1, '#00FFFF', '🛡️', 300.0),
  ('Personal', 1, '#FF00FF', '👤', 100.0),
  ('Debt', 1, '#A52A2A', '💳', 400.0),
  ('Savings', 1, '#008080', '💰', 500.0),
  ('Gifts', 1, '#FFFF00', '🎁', 100.0),
  ('Education', 1, '#808080', '📚', 400.0),
  ('Income', 2, '#000000', '💼', 0.0),
  ('Subscriptions', 1, '#4B0082', '📱', 50.0),
  ('Others', 1, '#D3D3D3', '❓', 250.0);

CREATE TABLE SubCategory (
  ID int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name varchar(200) not null,
  categoryId int not null,
  CONSTRAINT fk_category
  FOREIGN KEY (categoryId)
    REFERENCES category(ID), 
  UNIQUE (NAME, categoryId)
);

INSERT INTO SubCategory (Name, CategoryId)
VALUES 
  ('Rent', 1),
  ('Credit', 1),
  ('Condominium', 1),
  ('Electricity and Gas', 1),
  ('Water', 1),
  ('Internet', 1),
  ('Public Transport', 2),
  ('Fuel', 2),
  ('Car Inspection', 2),
  ('Car Maintenance', 2),
  ('Parking fee', 2),
  ('Groceries', 3),
  ('Restaurants', 3),
  ('Coffee Shop', 3),
  ('Bakery', 3),
  ('Phone', 4),
  ('Movies', 5),
  ('Concerts', 5),
  ('Games', 5),
  ('Dentist', 6),
  ('Hospital', 6),
  ('Pharmacy', 6),
  ('Psychiatrist', 6),
  ('Exams', 6),
  ('Health', 7),
  ('House', 7),
  ('Gym', 8),
  ('Haircut', 8),
  ('Clothing', 8),
  ('Shoes', 8),
  ('Credit Cards', 9),
  ('House', 10),
  ('Birthday', 11), 
  ('Wedding', 11),
  ('Birthday', 13), 
  ('Holidays', 13), 
  ('Salary', 13),
  ('Spotify', 14),
  ('Apple', 14),
  ('Netflix', 14),
  ('Disney', 14),
  ('Prime', 14),
  ('HBO', 14),
  ('Youtube Premium', 14);

CREATE TABLE ClassificationRule (
  ID int GENERATED ALWAYS AS IDENTITY PRIMARY KEY, 
  Pattern varchar(200) NOT NULL,
  MatchType varchar(10) NOT NULL DEFAULT 'contains' CHECK (MatchType IN ('contains', 'starts_with', 'exact', 'regex')), 
  CategoryId int NOT NULL REFERENCES CATEGORY(Id),
  SubCategoryId int NULL REFERENCES SubCategory(Id)
);

CREATE INDEX idx_rule_pattern on ClassificationRule (LOWER(pattern));

CREATE TABLE Bank (
  ID int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  NAME text not null,
  Abbreviation text not null,
  DatePattern text not null,
  DateEncoding text not null
);

INSERT INTO Bank (Name, Abbreviation, DatePattern, DateEncoding)
VALUES 
  ('Caixa Geral Depósitos', 'CGD', 'r"(\d{2}[/-]\d{2}[/-]\d{4})"', 'latin1' ),
  ('Millennium BCP', 'BCP', 'r"(\d{4}[/-]\d{2}[/-]\d{2})"', 'utf-8'),
  ('Novo Banco', 'NB', 'r"(\d{2}[/-]\d{2}[/-]\d{4})"', 'utf-8'),
  ('Santander', 'Santander', 'r"(\d{2}[/-]\d{2}[/-]\d{4})"', 'latin1'),
  ('Banco BPI', 'BPI', 'r"(\d{2}[/-]\d{2}[/-]\d{4})"', 'utf-8');

CREATE TABLE Account (
  ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  NAME VARCHAR(20) NOT NULL UNIQUE,
  Iban varchar(34) NOT NULL UNIQUE, 
  BankId int not null references Bank(Id), 
  Currency char(3) NOT NULL, 
  AccountTypeId int not null references AccountType(ID),
  CurrentBalance numeric(14, 2) not null
);

CREATE TABLE BankTransaction (
  ID int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  AccountId int not null References Account(Id), 
  OperationDate DATE not null,
  ValueDate Date, 
  Description Text not null,
  Amount numeric(14, 2) not null,
  AccountingBalance numeric(14, 2) not null,
  CategoryId int not null REFERENCES CATEGORY(Id),
  SubCategoryId int null References SubCategory(Id)
);

CREATE INDEX idx_tx_account_date ON BankTransaction (accountid, operationdate DESC);
CREATE INDEX idx_tx_category     ON BankTransaction (categoryid);
CREATE INDEX idx_tx_date         ON BankTransaction (operationdate DESC);

CREATE TABLE BankStatementExportFormat (
	ID int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	ColumnsExport text not null,
	BankId int not null references Bank(Id)
);

INSERT INTO BankStatementExportFormat (ColumnsExport, BankId)
VALUES 
	('Date;BalanceDate;Description;Expense;Income;Accounting Balance;Balance;Category', 1);

CREATE TABLE Budget (
  ID int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  CategoryId int NOT NULL REFERENCES Category(Id), 
  Year smallint NOT NULL, 
  MONTH SMALLINT NOT NULL, 
  Amount numeric (10, 2) NOT NULL, 
  Unique (CategoryId, YEAR, MONTH)
);

CREATE TABLE Transfer (
    id              SERIAL PRIMARY KEY,
    from_account_id INTEGER      NOT NULL REFERENCES Account(id),
    to_account_id   INTEGER      NOT NULL REFERENCES Account(id),
    amount          NUMERIC(14,2) NOT NULL,
    transfer_date   DATE         NOT NULL,
    description     TEXT,
    from_tx_id      INTEGER      REFERENCES BankTransaction(id),
    to_tx_id        INTEGER      REFERENCES BankTransaction(id)
);

CREATE TABLE MLTrainingSample (
    id              SERIAL PRIMARY KEY,
    description     TEXT    NOT NULL,
    category_id     INTEGER NOT NULL REFERENCES Category(id),
    sub_category_id INTEGER REFERENCES SubCategory(id),
    source          VARCHAR(20) DEFAULT 'manual'
                    CHECK (source IN ('manual','confirmed_ml','confirmed_rule')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
 
CREATE INDEX idx_ml_category ON MLTrainingSample (category_id);