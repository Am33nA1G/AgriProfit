import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableFooter,
} from '../table';

describe('Table Component', () => {
  it('renders table with headers and rows', () => {
    render(
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Price</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>Tomato</TableCell>
            <TableCell>₹50/kg</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Price')).toBeInTheDocument();
    expect(screen.getByText('Tomato')).toBeInTheDocument();
    expect(screen.getByText('₹50/kg')).toBeInTheDocument();
  });

  it('renders table caption', () => {
    render(
      <Table>
        <TableCaption>List of commodities</TableCaption>
        <TableBody>
          <TableRow>
            <TableCell>Data</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    
    expect(screen.getByText('List of commodities')).toBeInTheDocument();
  });

  it('renders table footer', () => {
    render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>Item 1</TableCell>
            <TableCell>₹100</TableCell>
          </TableRow>
        </TableBody>
        <TableFooter>
          <TableRow>
            <TableCell>Total</TableCell>
            <TableCell>₹100</TableCell>
          </TableRow>
        </TableFooter>
      </Table>
    );
    
    expect(screen.getByText('Total')).toBeInTheDocument();
  });

  it('renders multiple rows correctly', () => {
    render(
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Commodity</TableHead>
            <TableHead>Quantity</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>Rice</TableCell>
            <TableCell>100kg</TableCell>
          </TableRow>
          <TableRow>
            <TableCell>Wheat</TableCell>
            <TableCell>50kg</TableCell>
          </TableRow>
          <TableRow>
            <TableCell>Sugar</TableCell>
            <TableCell>25kg</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    
    expect(screen.getByText('Rice')).toBeInTheDocument();
    expect(screen.getByText('Wheat')).toBeInTheDocument();
    expect(screen.getByText('Sugar')).toBeInTheDocument();
  });

  it('applies custom className to table', () => {
    const { container } = render(
      <Table className="custom-table">
        <TableBody>
          <TableRow>
            <TableCell>Data</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    
    const table = container.querySelector('table');
    expect(table).toHaveClass('custom-table');
  });

  it('renders empty table structure', () => {
    render(
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Column 1</TableHead>
            <TableHead>Column 2</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell colSpan={2} className="text-center">
              No data available
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    
    expect(screen.getByText('No data available')).toBeInTheDocument();
  });

  it('handles complex table with multiple columns', () => {
    render(
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>ID</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>Price</TableHead>
            <TableHead>Stock</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>1</TableCell>
            <TableCell>Tomato</TableCell>
            <TableCell>Vegetable</TableCell>
            <TableCell>₹50</TableCell>
            <TableCell>Available</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    
    expect(screen.getByText('ID')).toBeInTheDocument();
    expect(screen.getByText('Category')).toBeInTheDocument();
    expect(screen.getByText('Stock')).toBeInTheDocument();
  });

  it('supports responsive wrapper', () => {
    const { container } = render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>Data</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    
    const wrapper = container.querySelector('.overflow-auto');
    expect(wrapper).toBeInTheDocument();
  });
});
