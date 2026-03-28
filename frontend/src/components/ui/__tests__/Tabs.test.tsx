import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../tabs';

describe('Tabs Component', () => {
  it('renders tabs with triggers and content', () => {
    render(
      <Tabs value="tab1" onValueChange={() => {}}>
        <TabsList>
          <TabsTrigger value="tab1">Tab 1</TabsTrigger>
          <TabsTrigger value="tab2">Tab 2</TabsTrigger>
        </TabsList>
        <TabsContent value="tab1">Content 1</TabsContent>
        <TabsContent value="tab2">Content 2</TabsContent>
      </Tabs>
    );
    
    expect(screen.getByText('Tab 1')).toBeInTheDocument();
    expect(screen.getByText('Tab 2')).toBeInTheDocument();
    expect(screen.getByText('Content 1')).toBeInTheDocument();
  });

  it('shows only active tab content', () => {
    render(
      <Tabs value="tab1" onValueChange={() => {}}>
        <TabsList>
          <TabsTrigger value="tab1">Tab 1</TabsTrigger>
          <TabsTrigger value="tab2">Tab 2</TabsTrigger>
        </TabsList>
        <TabsContent value="tab1">First Content</TabsContent>
        <TabsContent value="tab2">Second Content</TabsContent>
      </Tabs>
    );
    
    expect(screen.getByText('First Content')).toBeInTheDocument();
    expect(screen.queryByText('Second Content')).not.toBeInTheDocument();
  });

  it('calls onValueChange when tab clicked', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();
    
    render(
      <Tabs value="tab1" onValueChange={handleChange}>
        <TabsList>
          <TabsTrigger value="tab1">Tab 1</TabsTrigger>
          <TabsTrigger value="tab2">Tab 2</TabsTrigger>
        </TabsList>
        <TabsContent value="tab1">Content 1</TabsContent>
        <TabsContent value="tab2">Content 2</TabsContent>
      </Tabs>
    );
    
    await user.click(screen.getByText('Tab 2'));
    expect(handleChange).toHaveBeenCalledWith('tab2');
  });

  it('highlights active tab', () => {
    const { container } = render(
      <Tabs value="tab2" onValueChange={() => {}}>
        <TabsList>
          <TabsTrigger value="tab1">Tab 1</TabsTrigger>
          <TabsTrigger value="tab2">Tab 2</TabsTrigger>
        </TabsList>
      </Tabs>
    );
    
    const activeTab = screen.getByText('Tab 2');
    expect(activeTab).toHaveClass('bg-background', 'text-foreground');
  });

  it('renders multiple tab panels', () => {
    render(
      <Tabs value="prices" onValueChange={() => {}}>
        <TabsList>
          <TabsTrigger value="prices">Prices</TabsTrigger>
          <TabsTrigger value="trends">Trends</TabsTrigger>
          <TabsTrigger value="forecast">Forecast</TabsTrigger>
        </TabsList>
        <TabsContent value="prices">Price data</TabsContent>
        <TabsContent value="trends">Trend data</TabsContent>
        <TabsContent value="forecast">Forecast data</TabsContent>
      </Tabs>
    );
    
    expect(screen.getByText('Prices')).toBeInTheDocument();
    expect(screen.getByText('Trends')).toBeInTheDocument();
    expect(screen.getByText('Forecast')).toBeInTheDocument();
    expect(screen.getByText('Price data')).toBeInTheDocument();
  });

  it('applies custom className to TabsList', () => {
    const { container } = render(
      <Tabs value="tab1" onValueChange={() => {}}>
        <TabsList className="custom-tabs-list">
          <TabsTrigger value="tab1">Tab 1</TabsTrigger>
        </TabsList>
      </Tabs>
    );
    
    const tabsList = container.querySelector('.custom-tabs-list');
    expect(tabsList).toBeInTheDocument();
  });

  it('switches content when tab changes', async () => {
    const user = userEvent.setup();
    let currentValue = 'tab1';
    const handleChange = (value: string) => {
      currentValue = value;
    };
    
    const { rerender } = render(
      <Tabs value={currentValue} onValueChange={handleChange}>
        <TabsList>
          <TabsTrigger value="tab1">Tab 1</TabsTrigger>
          <TabsTrigger value="tab2">Tab 2</TabsTrigger>
        </TabsList>
        <TabsContent value="tab1">Content A</TabsContent>
        <TabsContent value="tab2">Content B</TabsContent>
      </Tabs>
    );
    
    expect(screen.getByText('Content A')).toBeInTheDocument();
    
    await user.click(screen.getByText('Tab 2'));
    
    rerender(
      <Tabs value="tab2" onValueChange={handleChange}>
        <TabsList>
          <TabsTrigger value="tab1">Tab 1</TabsTrigger>
          <TabsTrigger value="tab2">Tab 2</TabsTrigger>
        </TabsList>
        <TabsContent value="tab1">Content A</TabsContent>
        <TabsContent value="tab2">Content B</TabsContent>
      </Tabs>
    );
    
    expect(screen.getByText('Content B')).toBeInTheDocument();
  });
});
