export type RunStatus =
  | 'running'
  | 'awaiting_approval'
  | 'completed'
  | 'rejected'
  | 'failed';

export interface ToolCallRecord {
  tool_name: string;
  input_arguments: Record<string, any>;
  output: any;
  execution_time_ms: number;
  error?: string | null;
}

export interface StepTrace {
  step_index: number;
  agent_name: string;
  timestamp: string;
  input_data: Record<string, any>;
  output_data: Record<string, any>;
  confidence: number;
  tool_calls: ToolCallRecord[];
  escalation_triggered: boolean;
  escalation_reason?: string | null;
}

export interface RunResponse {
  run_id: string;
  session_id: string;
  pack_name: string;
  status: RunStatus;
  confidence: number;
  current_agent?: string | null;
  input_data: Record<string, any>;
  final_output?: Record<string, any> | null;
  escalation_reason?: string | null;
  trace_steps: StepTrace[];
  created_at: string;
  updated_at: string;
}

export interface AgentDefinition {
  name: string;
  role: string;
  system_prompt: string;
  allowed_tools: string[];
}

export interface DomainPack {
  name: string;
  version: string;
  description: string;
  default_confidence_threshold: number;
  entry_agent: string;
  confidence_thresholds: Record<string, number>;
  agents: AgentDefinition[];
  routing_rules: Array<{
    from_agent: string;
    condition_type: string;
    condition_expression?: string | null;
    to_agent: string;
  }>;
  escalation_rules: Array<{
    condition: string;
    reason: string;
    auto_escalate: boolean;
  }>;
}

export interface PackSummary {
  name: string;
  version: string;
  description: string;
  default_confidence_threshold: number;
  entry_agent: string;
  agents: string[];
}
