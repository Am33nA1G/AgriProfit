import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatsCard } from '../StatsGrid';

describe('StatsCard Component', () => {
  it('renders with value and label', () => {
    render(
      <StatsCard
        value="150"
        label="Total Sales"
        trend="+12.5%"
      />
    );
    
    expect(screen.getByText('150')).toBeInTheDocument();
    expect(screen.getByText('Total Sales')).toBeInTheDocument();
  });

  it('displays positive trend with up arrow', () => {
    render(
      <StatsCard
        value="1,234"
        label="Inventory Items"
        trend="+8.2%"
      />
    );
    
    expect(screen.getByText('+8.2%')).toBeInTheDocument();
    const trendIcon = screen.getByText('+8.2%').previousElementSibling;
    expect(trendIcon).toBeInTheDocument();
  });

  it('displays negative trend with down arrow', () => {
    render(
      <StatsCard
        value="45"
        label="Pending Orders"
        trend="-5.1%"
      />
    );
    
    expect(screen.getByText('-5.1%')).toBeInTheDocument();
  });

  it('renders highlighted variant', () => {
    const { container } = render(
      <StatsCard
        value="₹50,000"
        label="Revenue"
        trend="+15.3%"
        isHighlighted={true}
      />
    );
    
    expect(screen.getByText('₹50,000')).toBeInTheDocument();
    const card = container.querySelector('.bg-\\[\\#166534\\]');
    expect(card).toBeInTheDocument();
  });

  it('renders non-highlighted variant by default', () => {
    const { container } = render(
      <StatsCard
        value="25"
        label="Active Users"
        trend="+3.0%"
      />
    );
    
    expect(screen.getByText('25')).toBeInTheDocument();
    const card = container.querySelector('.bg-white');
    expect(card).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <StatsCard
        value="100"
        label="Test"
        trend="+10%"
        className="custom-stat-card"
      />
    );
    
    const card = container.querySelector('.custom-stat-card');
    expect(card).toBeInTheDocument();
  });

  it('renders trend suffix text', () => {
    render(
      <StatsCard
        value="500"
        label="Products"
        trend="+20%"
      />
    );
    
    expect(screen.getByText('from last month')).toBeInTheDocument();
  });

  it('renders action button with arrow icon', () => {
    const { container } = render(
      <StatsCard
        value="123"
        label="Metric"
        trend="+5%"
      />
    );
    
    const button = container.querySelector('button');
    expect(button).toBeInTheDocument();
    
    const arrowIcon = container.querySelector('svg');
    expect(arrowIcon).toBeInTheDocument();
  });

  it('handles large values correctly', () => {
    render(
      <StatsCard
        value="1,234,567"
        label="Total Revenue"
        trend="+45.2%"
      />
    );
    
    expect(screen.getByText('1,234,567')).toBeInTheDocument();
  });

  it('handles zero trend', () => {
    render(
      <StatsCard
        value="100"
        label="Stable Metric"
        trend="0%"
      />
    );
    
    expect(screen.getByText('0%')).toBeInTheDocument();
  });
});
