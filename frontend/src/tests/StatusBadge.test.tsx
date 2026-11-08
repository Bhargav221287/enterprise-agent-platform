import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { StatusBadge } from '../components/StatusBadge';

describe('StatusBadge Component', () => {
  it('renders completed status correctly', () => {
    render(<StatusBadge status="completed" />);
    const badge = screen.getByTestId('status-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('Completed');
    expect(badge).toHaveClass('badge-completed');
  });

  it('renders awaiting_approval status with formatted label', () => {
    render(<StatusBadge status="awaiting_approval" />);
    const badge = screen.getByTestId('status-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('Awaiting Approval');
    expect(badge).toHaveClass('badge-awaiting_approval');
  });

  it('renders rejected status correctly', () => {
    render(<StatusBadge status="rejected" />);
    const badge = screen.getByTestId('status-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('Rejected');
    expect(badge).toHaveClass('badge-rejected');
  });
});
