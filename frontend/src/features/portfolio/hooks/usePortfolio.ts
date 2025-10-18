import { useState } from 'react';
import axios from 'axios';

export interface Holding {
  symbol: string;
  quantity: number;
  bookValue: number;
  marketValue: number;
}

export const usePortfolio = () => {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHoldings = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get('/api/holdings');
      setHoldings(response.data);
    } catch (err) {
      setError('Failed to fetch holdings. Please authenticate.');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { holdings, loading, error, fetchHoldings };
};