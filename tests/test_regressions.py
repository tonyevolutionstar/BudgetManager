import io
import math
from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
from data.database import _to_native
from service import FileImporterService as importer
from src.utils.date import apply_date_filter


class DatabaseValueTests(unittest.TestCase):
    def test_real_amounts_and_zero_are_not_converted_to_null(self):
        for value in (52.90, 0.0, -150.25, np.float64(123.45)):
            self.assertEqual(_to_native(value), float(value))

    def test_only_missing_and_nonfinite_numbers_become_null(self):
        for value in (None, pd.NA, pd.NaT, float('nan'), float('inf'), np.float64('-inf')):
            self.assertIsNone(_to_native(value))
        self.assertEqual(_to_native(np.int64(12)), 12)


class ImportTests(unittest.TestCase):
    def test_short_csv_reports_a_user_error_instead_of_keyerror(self):
        csv = io.BytesIO(b'Date;Description;Amount\n13/11/2026;Test;5\n')
        with self.assertRaises(importer.StatementImportError):
            importer.load_csv_file(csv)

    def test_pdf_passes_a_rewound_file_object_not_a_nonexistent_name(self):
        pdf = MagicMock()
        pdf.pages = [MagicMock()]
        pdf.__enter__.return_value = pdf
        result = {'transactions': [{'date': '03/04/2026', 'description': 'Compra',
            'debit': 52.9, 'credit': 0, 'balance': 947.1, 'category': 'Food'}]}
        with patch.object(importer.pdfplumber, 'open', return_value=pdf), patch.object(
                importer.BankStatementExtractor, 'process_statement', return_value=result) as extract:
            frame = importer.load_pdf_file(io.BytesIO(b'%PDF-test'))
            source = extract.call_args.args[0]
            self.assertIsInstance(source, io.BytesIO)
            self.assertEqual(source.tell(), 0)
            self.assertEqual(frame.iloc[0]['Expense'], 52.9)
            self.assertEqual(frame.iloc[0]['Balance'], 947.1)
            self.assertEqual(frame.iloc[0]['Date'], pd.Timestamp('2026-04-03'))

    def test_saved_csv_roundtrip_preserves_dates_amounts_and_categories(self):
        frame = pd.DataFrame([{'Date':pd.Timestamp('2026-04-03'),
            'BalanceDate':pd.Timestamp('2026-04-04'), 'Description':'Compra; Continente',
            'Expense':52.9, 'Income':0, 'Accounting Balance':947.1,
            'Balance':947.1,'Category':'Custom Groceries'}], columns=importer.CSV_COLUMNS)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'personal.csv'
            importer.save_dataframe(frame, path)
            actual = importer.load_saved_transactions(path)
            self.assertEqual(actual.iloc[0]['Date'], frame.iloc[0]['Date'])
            self.assertEqual(actual.iloc[0]['BalanceDate'], frame.iloc[0]['BalanceDate'])
            self.assertEqual(actual.iloc[0]['Expense'], 52.9)
            self.assertEqual(actual.iloc[0]['Category'], 'Custom Groceries')
            self.assertEqual(actual.iloc[0]['Description'], 'Compra; Continente')

    def test_first_run_without_csv_is_empty(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(importer.load_saved_transactions(Path(folder) / 'missing.csv').empty)

    def test_custom_filter_keeps_only_requested_dates(self):
        frame = pd.DataFrame({'Date':['03/04/2026','05/04/2026'],'Expense':[10,20]})
        actual = apply_date_filter(frame, 'Custom Range', date(2026,4,3), date(2026,4,3))
        self.assertEqual(actual['Expense'].tolist(), [10])

if __name__ == '__main__':
    unittest.main()
