import React from 'react';
import { RunStatus } from '../types';

interface StatusBadgeProps {
  status: RunStatus;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const formatLabel = (s: string) => {
    switch (s) {
      case 'awaiting_approval':
        return 'Awaiting Approval';
      default:
        return s.charAt(0).toUpperCase() + s.slice(1);
    }
  };

  return (
    <span className={`badge badge-${status}`} data-testid="status-badge">
      <span
        style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          backgroundColor: 'currentColor',
          display: 'inline-block',
        }}
      />
      {formatLabel(status)}
    </span>
  );
};
