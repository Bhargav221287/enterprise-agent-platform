import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { RunWorkflowForm } from '../components/RunWorkflowForm';
import { PackSummary } from '../types';

const mockPacks: PackSummary[] = [
  {
    name: 'it_ticket_triage',
    version: '1.0.0',
    description: 'IT incident automated classification',
    default_confidence_threshold: 0.75,
    entry_agent: 'classifier',
    agents: ['classifier', 'resolver', 'reviewer'],
  },
  {
    name: 'loan_prescreening',
    version: '1.0.0',
    description: 'Loan prescreening and compliance',
    default_confidence_threshold: 0.8,
    entry_agent: 'intake',
    agents: ['intake', 'underwriter', 'compliance'],
  },
];

describe('RunWorkflowForm Component', () => {
  it('renders domain pack options in select menu', () => {
    render(<RunWorkflowForm packs={mockPacks} onRunCreated={vi.fn()} />);

    expect(screen.getByLabelText(/domain pack/i)).toBeInTheDocument();
    const matches = screen.getAllByText(/it incident automated classification/i);
    expect(matches.length).toBeGreaterThan(0);
  });

  it('updates JSON input when scenario preset button is clicked', () => {
    render(<RunWorkflowForm packs={mockPacks} onRunCreated={vi.fn()} />);

    const critBtn = screen.getByText(/critical security breach/i);
    fireEvent.click(critBtn);

    const textarea = screen.getByLabelText(/input data payload/i) as HTMLTextAreaElement;
    expect(textarea.value).toContain('critical database unauthorized');
  });

  it('renders submit button with active state', () => {
    render(<RunWorkflowForm packs={mockPacks} onRunCreated={vi.fn()} />);

    const submitBtn = screen.getByRole('button', { name: /start workflow run/i });
    expect(submitBtn).toBeInTheDocument();
    expect(submitBtn).not.toBeDisabled();
  });
});
