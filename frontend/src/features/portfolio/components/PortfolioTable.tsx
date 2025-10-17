import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { Holding } from '../types';

interface PortfolioTableProps {
  holdings: Holding[];
}

const PortfolioTable = ({ holdings }: PortfolioTableProps) => {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Symbol</TableHead>
          <TableHead>Quantity</TableHead>
          <TableHead>Book Value</TableHead>
          <TableHead>Market Value</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {holdings.map((holding, index) => (
          <TableRow key={index}>
            <TableCell>{holding.symbol}</TableCell>
            <TableCell>{holding.quantity}</TableCell>
            <TableCell>${holding.bookValue.toFixed(2)}</TableCell>
            <TableCell>${holding.marketValue.toFixed(2)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};

export default PortfolioTable;