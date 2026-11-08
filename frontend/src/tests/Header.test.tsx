import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Header } from '../components/Header';

describe('Header Component', () => {
  it('renders application branding and title', () => {
    render(
      <Header
        activeTab="run"
        setActiveTab={() => {}}
        selectedRunId={null}
        serverHealth={true}
      />
    );
    expect(screen.getByText('Enterprise Agent Platform')).toBeInTheDocument();
    expect(screen.getByText('System Operational')).toBeInTheDocument();
  });

  it('highlights the active tab button', () => {
    render(
      <Header
        activeTab="list"
        setActiveTab={() => {}}
        selectedRunId={null}
        serverHealth={true}
      />
    );
    const listBtn = screen.getByText('Workflows List');
    expect(listBtn).toHaveClass('active');
  });

  it('triggers setActiveTab callback on click', () => {
    const onTabChange = vi.fn();
    render(
      <Header
        activeTab="run"
        setActiveTab={onTabChange}
        selectedRunId={null}
        serverHealth={true}
      />
    );
    const listBtn = screen.getByText('Workflows List');
    fireEvent.click(listBtn);
    expect(onTabChange).toHaveBeenCalledWith('list');
  });
});
