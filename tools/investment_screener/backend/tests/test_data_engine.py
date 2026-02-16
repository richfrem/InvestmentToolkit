import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from QuestradeDataEngine import QuestradeSyncEngine

class TestQuestradeDataEngine(unittest.TestCase):
    def setUp(self):
        self.output_file = "test_portfolio.json"
        self.engine = QuestradeSyncEngine(cache_dir=".", output_file=self.output_file)

    def tearDown(self):
        if os.path.exists(self.output_file):
            os.remove(self.output_file)

    @patch('utils.QuestradeAPIClient.QuestradeAPIClient.get_accounts')
    @patch('utils.QuestradeAPIClient.QuestradeAPIClient.get_positions')
    @patch('utils.QuestradeTokenManager.QuestradeTokenManager.load_tokens')
    def test_end_to_end_sync(self, mock_load, mock_positions, mock_accounts):
        # Setup Mocks
        mock_load.return_value = {"access_token": "valid", "api_server": "https://api.test"}
        mock_accounts.return_value = [{"number": "123", "type": "TFSA"}, {"number": "456", "type": "RRSP"}]
        
        # Mock positions with overlapping symbols (AAPL and MSFT)
        mock_positions.side_effect = [
            [
                {"symbol": "AAPL.US", "openQuantity": 10, "currentPrice": 150.0},
                {"symbol": "MSFT.US", "openQuantity": 5, "currentPrice": 300.0}
            ],
            [
                {"symbol": "AAPL.US", "openQuantity": 5, "currentPrice": 155.0}
            ]
        ]

        # Run Sync
        success = self.engine.run_sync()
        self.assertTrue(success)

        # Verify Results
        import json
        with open(self.output_file, "r") as f:
            data = json.load(f)

        # Should have 2 unique symbols
        self.assertEqual(len(data), 2)
        
        # Verify aggregation (10 + 5 = 15 AAPL)
        aapl = next(p for p in data if p["symbol"] == "AAPL")
        self.assertEqual(aapl["shares"], 15)
        # Verify price (should be the latest one encountered, or handled by logic)
        self.assertIn(aapl["price"], [150.0, 155.0])
        
        msft = next(p for p in data if p["symbol"] == "MSFT")
        self.assertEqual(msft["shares"], 5)

if __name__ == "__main__":
    unittest.main()
