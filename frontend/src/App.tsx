import React, { useState, useCallback, useEffect } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  BackgroundVariant,
} from '@xyflow/react';
import type { Connection, Edge, Node } from '@xyflow/react';

import { DecisionNode } from './components/DecisionNode';
import { DecisionEdge } from './components/DecisionEdge';
import { NodeEditor } from './components/NodeEditor';
import { ExecutionPanel } from './components/ExecutionPanel';
import { Toolbar } from './components/Toolbar';
import { Header } from './components/Header';
import type {
  DecisionNodeData,
  DecisionEdgeData,
  WorkflowRunResult,
  WorkflowTemplate,
  WorkflowExportJSON,
} from './types/workflow';

const nodeTypes = {
  decisionNode: DecisionNode,
};

const edgeTypes = {
  decisionEdge: DecisionEdge,
};

// Initial Starter Workflow
const INITIAL_NODES: Node<DecisionNodeData>[] = [
  {
    id: 'node-1',
    type: 'decisionNode',
    position: { x: 300, y: 80 },
    data: {
      label: 'Is this a support request?',
      prompt: 'Is the user requesting technical assistance, troubleshooting, or help using the application?',
      is_start: true,
      status: 'pending',
    },
  },
  {
    id: 'node-2',
    type: 'decisionNode',
    position: { x: 120, y: 280 },
    data: {
      label: 'Support Tier 1 Routing',
      prompt: 'Is the issue related to password reset or account login credentials?',
      is_start: false,
      status: 'pending',
    },
  },
  {
    id: 'node-3',
    type: 'decisionNode',
    position: { x: 480, y: 280 },
    data: {
      label: 'Sales & Product Inquiries',
      prompt: 'Is the user asking about enterprise pricing or upgrading to a paid subscription?',
      is_start: false,
      status: 'pending',
    },
  },
];

const INITIAL_EDGES: Edge<DecisionEdgeData>[] = [
  {
    id: 'e1-2',
    source: 'node-1',
    target: 'node-2',
    sourceHandle: 'yes',
    type: 'decisionEdge',
    data: { decision: 'YES', isActive: false },
  },
  {
    id: 'e1-3',
    source: 'node-1',
    target: 'node-3',
    sourceHandle: 'no',
    type: 'decisionEdge',
    data: { decision: 'NO', isActive: false },
  },
];

export const App: React.FC = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState(INITIAL_NODES);
  const [edges, setEdges, onEdgesChange] = useEdgesState(INITIAL_EDGES);

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [runResult, setRunResult] = useState<WorkflowRunResult | null>(null);
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [backendConnected, setBackendConnected] = useState(true);
  const [inputContext, setInputContext] = useState(
    'Customer message: Hello, I forgot my account password and cannot log into the dashboard.'
  );

  // Fetch templates and test backend connection on mount
  useEffect(() => {
    fetch('/api/workflows/templates')
      .then((res) => res.json())
      .then((data) => {
        setTemplates(data);
        setBackendConnected(true);
      })
      .catch((err) => {
        console.warn('Backend templates unreachable:', err);
        setBackendConnected(false);
      });
  }, []);

  // Delete node callback
  const handleDeleteNode = useCallback(
    (id: string) => {
      setNodes((nds) => nds.filter((n) => n.id !== id));
      setEdges((eds) => eds.filter((e) => e.source !== id && e.target !== id));
      setSelectedNodeId((cur) => (cur === id ? null : cur));
    },
    [setNodes, setEdges]
  );

  // Set start node callback
  const handleSetStartNode = useCallback(
    (id: string) => {
      setNodes((nds) =>
        nds.map((n) => ({
          ...n,
          data: {
            ...n.data,
            is_start: n.id === id,
          },
        }))
      );
    },
    [setNodes]
  );

  // Wire node action callbacks into node data
  const enhanceNodes = useCallback(
    (rawNodes: Node<DecisionNodeData>[]): Node<DecisionNodeData>[] => {
      return rawNodes.map((n) => ({
        ...n,
        data: {
          ...n.data,
          onEdit: (id: string) => setSelectedNodeId(id),
          onDelete: (id: string) => handleDeleteNode(id),
          onSetStart: (id: string) => handleSetStartNode(id),
        },
      }));
    },
    [handleDeleteNode, handleSetStartNode]
  );

  useEffect(() => {
    setNodes((nds) => enhanceNodes(nds));
  }, [enhanceNodes, setNodes]);

  // Connect handler: dynamically assign YES or NO decision based on handle
  const onConnect = useCallback(
    (params: Connection) => {
      const decision = params.sourceHandle === 'no' ? 'NO' : 'YES';
      const newEdge: Edge<DecisionEdgeData> = {
        ...params,
        id: `e-${params.source}-${params.target}-${decision.toLowerCase()}-${Date.now()}`,
        type: 'decisionEdge',
        sourceHandle: params.sourceHandle || (decision === 'NO' ? 'no' : 'yes'),
        data: { decision, isActive: false },
      };
      setEdges((eds) => addEdge(newEdge, eds));
    },
    [setEdges]
  );

  // Add new node
  const handleAddNode = () => {
    const newId = `node-${Date.now().toString().slice(-4)}`;
    const newNode: Node<DecisionNodeData> = {
      id: newId,
      type: 'decisionNode',
      position: {
        x: 250 + (nodes.length * 40) % 200,
        y: 150 + (nodes.length * 50) % 250,
      },
      data: {
        label: `Decision Step ${nodes.length + 1}`,
        prompt: 'Is this an urgent priority inquiry?',
        is_start: nodes.length === 0,
        status: 'pending',
        onEdit: (id: string) => setSelectedNodeId(id),
        onDelete: (id: string) => handleDeleteNode(id),
        onSetStart: (id: string) => handleSetStartNode(id),
      },
    };
    setNodes((nds) => [...nds, newNode]);
    setSelectedNodeId(newId);
  };

  // Save changes from NodeEditor
  const handleSaveNode = (
    id: string,
    label: string,
    prompt: string,
    isStart: boolean
  ) => {
    setNodes((nds) =>
      nds.map((n) => {
        if (n.id === id) {
          return {
            ...n,
            data: {
              ...n.data,
              label,
              prompt,
              is_start: isStart,
            },
          };
        }
        if (isStart && n.id !== id) {
          return {
            ...n,
            data: {
              ...n.data,
              is_start: false,
            },
          };
        }
        return n;
      })
    );
    setSelectedNodeId(null);
  };

  // Reset workflow
  const handleResetWorkflow = () => {
    if (confirm('Are you sure you want to reset the canvas to the starter workflow?')) {
      setNodes(enhanceNodes(INITIAL_NODES));
      setEdges(INITIAL_EDGES);
      setRunResult(null);
      setSelectedNodeId(null);
    }
  };

  // Load template
  const handleLoadTemplate = (template: WorkflowTemplate) => {
    const rawNodes: Node<DecisionNodeData>[] = template.workflow.nodes.map((n) => ({
      id: n.id,
      type: 'decisionNode',
      position: n.position || { x: 100, y: 100 },
      data: {
        label: n.label,
        prompt: n.prompt,
        is_start: Boolean(n.is_start || n.id === template.workflow.start_node_id),
        status: 'pending',
      },
    }));

    const rawEdges: Edge<DecisionEdgeData>[] = template.workflow.edges.map((e, idx) => ({
      id: e.id || `e-${e.source}-${e.target}-${idx}`,
      source: e.source,
      target: e.target,
      sourceHandle: e.source_handle || (e.decision === 'NO' ? 'no' : 'yes'),
      type: 'decisionEdge',
      data: { decision: e.decision, isActive: false },
    }));

    setNodes(enhanceNodes(rawNodes));
    setEdges(rawEdges);
    setRunResult(null);
    setSelectedNodeId(null);
  };

  // Export JSON
  const handleExportJSON = () => {
    const startNode = nodes.find((n) => n.data.is_start) || nodes[0];
    const exportData: WorkflowExportJSON = {
      start_node_id: startNode?.id,
      input_context: inputContext,
      nodes: nodes.map((n) => ({
        id: n.id,
        label: n.data.label,
        prompt: n.data.prompt,
        is_start: Boolean(n.data.is_start),
        position: n.position,
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        decision: (e.data?.decision as 'YES' | 'NO') || 'YES',
        source_handle: e.sourceHandle || undefined,
      })),
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ai-workflow-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Import JSON
  const handleImportJSON = (json: WorkflowExportJSON) => {
    const importedNodes: Node<DecisionNodeData>[] = json.nodes.map((n) => ({
      id: n.id,
      type: 'decisionNode',
      position: n.position || { x: 100, y: 100 },
      data: {
        label: n.label || 'Decision Node',
        prompt: n.prompt || '',
        is_start: Boolean(n.is_start || n.id === json.start_node_id),
        status: 'pending',
      },
    }));

    const importedEdges: Edge<DecisionEdgeData>[] = (json.edges || []).map(
      (e, idx) => ({
        id: e.id || `e-${e.source}-${e.target}-${idx}`,
        source: e.source,
        target: e.target,
        sourceHandle: e.source_handle || (e.decision === 'NO' ? 'no' : 'yes'),
        type: 'decisionEdge',
        data: { decision: e.decision || 'YES', isActive: false },
      })
    );

    setNodes(enhanceNodes(importedNodes));
    setEdges(importedEdges);
    if (json.input_context) setInputContext(json.input_context);
    setRunResult(null);
    setSelectedNodeId(null);
  };

  // Run Workflow execution
  const handleRunWorkflow = async (contextText: string) => {
    if (nodes.length === 0) {
      alert('Cannot run an empty workflow. Please add at least one decision node.');
      return;
    }

    setIsRunning(true);
    setRunResult(null);

    // Reset node and edge visual states to pending
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: {
          ...n.data,
          status: 'pending',
          decision: undefined,
          error: undefined,
        },
      }))
    );
    setEdges((eds) =>
      eds.map((e) => ({
        ...e,
        data: {
          decision: e.data?.decision || 'YES',
          isActive: false,
        },
      }))
    );

    const startNode = nodes.find((n) => n.data.is_start) || nodes[0];
    const payload = {
      nodes: nodes.map((n) => ({
        id: n.id,
        label: n.data.label,
        prompt: n.data.prompt,
        is_start: Boolean(n.data.is_start),
        position: n.position,
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        decision: e.data?.decision || 'YES',
        source_handle: e.sourceHandle || (e.data?.decision === 'NO' ? 'no' : 'yes'),
      })),
      start_node_id: startNode.id,
      input_context: contextText.trim() || undefined,
    };

    try {
      const response = await fetch('/api/workflows/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({ detail: 'HTTP ' + response.status }));
        throw new Error(errJson.detail || 'Workflow execution failed');
      }

      const result: WorkflowRunResult = await response.json();
      setRunResult(result);

      // Animate execution traversal sequentially
      for (let i = 0; i < result.steps.length; i++) {
        const step = result.steps[i];
        const nextStep = result.steps[i + 1];

        // Highlight executing node
        setNodes((nds) =>
          nds.map((n) =>
            n.id === step.node_id
              ? {
                  ...n,
                  data: {
                    ...n.data,
                    status: step.status === 'completed' ? 'completed' : 'failed',
                    decision: step.decision || undefined,
                    error: step.error || undefined,
                  },
                }
              : n
          )
        );

        // Highlight edge leading to next node
        if (nextStep && step.decision) {
          setEdges((eds) =>
            eds.map((e) =>
              e.source === step.node_id &&
              e.target === nextStep.node_id &&
              e.data?.decision === step.decision
                ? {
                    ...e,
                    data: {
                      decision: e.data?.decision || 'YES',
                      isActive: true,
                    },
                  }
                : e
            )
          );
        }

        // Slight visual pacing for animation
        await new Promise((resolve) => setTimeout(resolve, 300));
      }
    } catch (err: unknown) {
      console.error('Workflow run error:', err);
      const errMessage = err instanceof Error ? err.message : 'Execution failed';
      setRunResult({
        run_id: `error_${Date.now()}`,
        status: 'failed',
        start_node_id: startNode.id,
        execution_path: [],
        steps: [],
        error: errMessage,
        created_at: new Date().toISOString(),
      });
    } finally {
      setIsRunning(false);
    }
  };

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) || null;

  return (
    <div className="w-screen h-screen relative bg-slate-950 overflow-hidden font-sans">
      {/* Header */}
      <Header
        backendConnected={backendConnected}
        nodeCount={nodes.length}
        edgeCount={edges.length}
      />

      {/* Floating Toolbar */}
      <Toolbar
        onAddNode={handleAddNode}
        onRunWorkflow={handleRunWorkflow}
        onResetWorkflow={handleResetWorkflow}
        onExportJSON={handleExportJSON}
        onImportJSON={handleImportJSON}
        onLoadTemplate={handleLoadTemplate}
        templates={templates}
        isRunning={isRunning}
        inputContext={inputContext}
        setInputContext={setInputContext}
      />

      {/* Main React Flow Canvas */}
      <div className="w-full h-full">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.2}
          maxZoom={1.8}
          proOptions={{ hideAttribution: true }}
          className="bg-slate-950"
        >
          <Background variant={BackgroundVariant.Dots} gap={20} size={1.2} color="#1e293b" />
          <Controls className="!bg-slate-900 !border-slate-700 !fill-slate-300 rounded-xl overflow-hidden shadow-xl" />
          <MiniMap
            nodeColor={(n) => {
              const nd = n.data as unknown as DecisionNodeData;
              if (nd?.is_start) return '#10b981';
              if (nd?.status === 'completed') return nd.decision === 'YES' ? '#22c55e' : '#f43f5e';
              return '#4f46e5';
            }}
            maskColor="rgba(15, 23, 42, 0.75)"
            className="!bg-slate-900/90 !border-slate-700 rounded-xl shadow-xl overflow-hidden"
          />
        </ReactFlow>
      </div>

      {/* Node Editor Drawer */}
      <NodeEditor
        nodeId={selectedNodeId}
        nodeData={selectedNode ? (selectedNode.data as unknown as DecisionNodeData) : null}
        onSave={handleSaveNode}
        onDelete={handleDeleteNode}
        onClose={() => setSelectedNodeId(null)}
      />

      {/* Execution Log Panel */}
      <ExecutionPanel runResult={runResult} isRunning={isRunning} />
    </div>
  );
};

export default App;
