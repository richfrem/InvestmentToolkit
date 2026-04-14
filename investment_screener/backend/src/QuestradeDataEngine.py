#!/usr/bin/env python3
"""
QuestradeDataEngine.py
=====================================

Purpose:
    Core sync engine that coordinates token management, API retrieval, and portfolio aggregation.

Layer: Retrieve

Usage:
    python QuestradeDataEngine.py --cache-dir . --output portfolio.json

Related:
    - QuestradeAPIClient.py
    - PortfolioAggregator.py
"""

import os
import sys
import logging
import argparse
from typing import Optional

# Setup Pathing
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

from utils.QuestradeTokenManager import QuestradeTokenManager
from utils.QuestradeAPIClient import QuestradeAPIClient
from utils.PortfolioAggregator import PortfolioAggregator
from utils.MetadataEnricher import MetadataEnricher

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QuestradeSyncEngine:
    """
    Coordinates the full lifecycle of a Questrade portfolio sync.
    """

    def __init__(self, cache_dir: str = ".", output_file: str = "portfolio.json"):
        """
        Initializes the sync engine.

        Args:
            cache_dir: Directory where the token cache is located.
            output_file: Target path for the aggregated portfolio JSON.
        """
        self.token_manager = QuestradeTokenManager(cache_dir=cache_dir)
        self.api_client = QuestradeAPIClient(self.token_manager)
        self.aggregator = PortfolioAggregator(output_path=output_file)
        self.enricher = MetadataEnricher()

    def run_sync(self) -> bool:
        """
        Executes the full sync lifecycle:
        1. Discover accounts
        2. Fetch positions & balances
        3. Aggregate holdings
        4. Save to portfolio.json

        Returns:
            True if sync completed successfully, False otherwise.
        """
        try:
            logger.info("Starting Questrade Portfolio Sync...")
            
            # 1. Fetch All Positions & Balances
            all_positions = self.api_client.get_all_positions()
            all_balances = self.api_client.get_all_balances()
            logger.info(f"Retrieved {len(all_positions)} raw position records and balances from {len(all_balances)} accounts.")
            
            # 2. Aggregate
            aggregated_holdings = self.aggregator.aggregate_positions(all_positions, balances=all_balances)
            logger.info(f"Aggregated into {len(aggregated_holdings)} unique holdings (including cash).")
            
            # 3. Enrich (ADR 018)
            self.enricher.enrich_holdings(aggregated_holdings)
            
            # 4. Save
            self.aggregator.save_portfolio(aggregated_holdings)
            logger.info(f"Successfully updated portfolio: {self.aggregator.output_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return False

def main():
    """Main entry point for the sync CLI."""
    parser = argparse.ArgumentParser(description="Questrade Portfolio Sync Engine")
    parser.add_argument("--cache-dir", default=".", help="Directory containing .questrade_cache")
    parser.add_argument("--output", default="../../frontend/src/data/portfolio.json", help="Path to portfolio.json")
    parser.add_argument("--seed", help="Seed a new manual refresh token")
    
    args = parser.parse_args()
    
    # Absolute pathing for reliability
    base_dir = os.getcwd()
    abs_output = os.path.abspath(os.path.join(base_dir, args.output))
    
    token_manager = QuestradeTokenManager(cache_dir=args.cache_dir)
    
    if args.seed:
        logger.info("Seeding new manual refresh token...")
        # Questrade requires at least a refresh_token to start rotation
        token_manager.save_tokens({"refresh_token": args.seed})
        logger.info("Token seeded successfully.")
        sys.exit(0)
        
    engine = QuestradeSyncEngine(cache_dir=args.cache_dir, output_file=abs_output)
    success = engine.run_sync()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
