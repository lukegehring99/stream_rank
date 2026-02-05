import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DataTable, Pagination } from '../components/DataTable';

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{ui}</BrowserRouter>
    </QueryClientProvider>
  );
};

interface TestItem {
  id: number;
  name: string;
  value: number;
}

const columns = [
  { key: 'name', header: 'Name' },
  { key: 'value', header: 'Value' },
];

const testData: TestItem[] = [
  { id: 1, name: 'Item 1', value: 100 },
  { id: 2, name: 'Item 2', value: 200 },
  { id: 3, name: 'Item 3', value: 300 },
];

describe('DataTable', () => {
  it('should render table headers', () => {
    renderWithProviders(
      <DataTable columns={columns} data={testData} keyField="id" />
    );

    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Value')).toBeInTheDocument();
  });

  it('should render table data', () => {
    renderWithProviders(
      <DataTable columns={columns} data={testData} keyField="id" />
    );

    expect(screen.getByText('Item 1')).toBeInTheDocument();
    expect(screen.getByText('Item 2')).toBeInTheDocument();
    expect(screen.getByText('Item 3')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('should show loading skeleton when isLoading is true', () => {
    renderWithProviders(
      <DataTable columns={columns} data={[]} keyField="id" isLoading={true} />
    );

    // Check for skeleton elements (using class name check)
    const skeletons = document.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('should show empty message when data is empty', () => {
    renderWithProviders(
      <DataTable
        columns={columns}
        data={[]}
        keyField="id"
        emptyMessage="No items found"
      />
    );

    expect(screen.getByText('No items found')).toBeInTheDocument();
  });

  it('should render custom cell content with render function', () => {
    const columnsWithRender = [
      {
        key: 'name',
        header: 'Name',
        render: (item: TestItem) => <strong>{item.name}</strong>,
      },
      { key: 'value', header: 'Value' },
    ];

    renderWithProviders(
      <DataTable columns={columnsWithRender} data={testData} keyField="id" />
    );

    const strongElements = document.querySelectorAll('strong');
    expect(strongElements.length).toBe(3);
  });
});

describe('Pagination', () => {
  it('should render page numbers', () => {
    renderWithProviders(
      <Pagination
        currentPage={1}
        totalPages={5}
        onPageChange={() => {}}
        totalItems={50}
        pageSize={10}
      />
    );

    // Use getAllByText since numbers may appear multiple times (in pagination and in "Showing X to Y")
    expect(screen.getAllByText('1').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('should show item count', () => {
    renderWithProviders(
      <Pagination
        currentPage={1}
        totalPages={5}
        onPageChange={() => {}}
        totalItems={50}
        pageSize={10}
      />
    );

    // Check the "Showing X to Y of Z results" text exists
    expect(screen.getByText(/Showing/)).toBeInTheDocument();
    expect(screen.getByText(/results/)).toBeInTheDocument();
    expect(screen.getAllByText('10').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('50').length).toBeGreaterThanOrEqual(1);
  });

  it('should highlight current page', () => {
    renderWithProviders(
      <Pagination
        currentPage={3}
        totalPages={5}
        onPageChange={() => {}}
        totalItems={50}
        pageSize={10}
      />
    );

    const currentPageButton = screen.getAllByText('3')[0];
    expect(currentPageButton).toHaveClass('bg-primary-600');
  });

  it('should not render when totalPages is 1', () => {
    const { container } = renderWithProviders(
      <Pagination
        currentPage={1}
        totalPages={1}
        onPageChange={() => {}}
        totalItems={10}
        pageSize={10}
      />
    );

    expect(container.firstChild).toBeNull();
  });
});
