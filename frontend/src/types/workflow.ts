export type DecisionType = 'YES' | 'NO';

export type NodeExecutionStatus = 'pending' | 'executing' | 'completed' | 'failed';

export interface DecisionNodeData extends Record<string, unknown> {
  label: string;
  prompt: string;
  is_start?: boolean;
  status?: NodeExecutionStatus;
  decision?: DecisionType;
  error?: string;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
  onSetStart?: (id: string) => void;
}

export interface DecisionEdgeData extends Record<string, unknown> {
  decision: DecisionType;
  isActive?: boolean;
}

export interface StepExecution {
  step_number: number;
  node_id: string;
  node_label: string;
  prompt: string;
  decision: DecisionType | null;
  status: 'completed' | 'failed' | 'executing';
  error?: string | null;
  raw_response?: string | null;
  timestamp: string;
}

export interface WorkflowRunResult {
  run_id: string;
  status: 'completed' | 'failed' | 'running';
  start_node_id: string;
  input_context?: string | null;
  execution_path: string[];
  steps: StepExecution[];
  error?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface WorkflowExportJSON {
  start_node_id?: string;
  input_context?: string;
  nodes: Array<{
    id: string;
    label: string;
    prompt: string;
    is_start?: boolean;
    position: { x: number; y: number };
  }>;
  edges: Array<{
    id?: string;
    source: string;
    target: string;
    decision: DecisionType;
    source_handle?: string;
  }>;
}

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  workflow: WorkflowExportJSON;
}
