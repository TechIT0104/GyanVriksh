import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph3D from "react-force-graph-3d";
import { get } from "../api/client";
import { useHighlight } from "../store/highlight";

const NODE_COLORS: Record<string, string> = {
  Equipment: "#f97316", Document: "#3b82f6", Procedure: "#22c55e",
  Regulation: "#ef4444", Incident: "#a855f7", Person: "#eab308",
  KnowledgeCapsule: "#F5C542", WorkOrder: "#06b6d4", SparePart: "#94a3b8",
};

export default function GraphExplorer() {
  const fgRef = useRef<any>(null);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<Set<string>>(new Set(Object.keys(NODE_COLORS)));
  const [selectedNode, setSelectedNode] = useState<any>(null);

  const { data } = useQuery({ queryKey: ["graph"], queryFn: () => get("/graph/nodes?limit=800"), retry: false });

  const hl = useHighlight();
  const hlSet = useMemo(() => new Set(hl.nodes.map((n) => String(n).toUpperCase())), [hl.nodes]);

  const graphData = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    const nodes = data.nodes
      .filter((n: any) => n.labels.some((l: string) => typeFilter.has(l)))
      .map((n: any) => {
        const name = n.props.tag_id || n.props.name || n.props.doc_id || n.props.proc_id ||
              n.props.reg_id || n.props.incident_id || n.props.wo_id || n.props.capsule_id || n.labels[0];
        return {
          id: n.id, label: n.labels[0], name, props: n.props,
          color: NODE_COLORS[n.labels[0]] || "#64748b",
          val: n.labels[0] === "KnowledgeCapsule" ? 6 : n.labels[0] === "Equipment" ? 5 : 3,
          highlighted: hlSet.has(String(name).toUpperCase()),
        };
      });
    const ids = new Set(nodes.map((n: any) => n.id));
    const links = data.links
      .filter((l: any) => ids.has(l.source) && ids.has(l.target))
      .map((l: any) => ({ ...l }));
    return { nodes, links };
  }, [data, typeFilter, hlSet]);

  // when the copilot highlights nodes from an answer, fly the camera to them
  useEffect(() => {
    if (!hlSet.size || !fgRef.current) return;
    const t = setTimeout(() => {
      try { fgRef.current.zoomToFit(1200, 80, (n: any) => n.highlighted); } catch { /* layout not ready */ }
    }, 400);
    return () => clearTimeout(t);
  }, [hlSet, graphData]);

  function doSearch() {
    const node = graphData.nodes.find((n: any) =>
      String(n.name).toLowerCase().includes(search.toLowerCase()));
    if (node && fgRef.current) {
      fgRef.current.cameraPosition(
        { x: (node as any).x + 60, y: (node as any).y + 60, z: (node as any).z + 60 },
        node, 1500);
      setSelectedNode(node);
    }
  }

  return (
    <div className="h-screen relative">
      <div className="absolute top-0 left-0 right-0 z-10 p-3 flex gap-3 items-center bg-navy-900/80 backdrop-blur border-b border-navy-600">
        <h1 className="font-bold text-gold-400 shrink-0">Knowledge Graph</h1>
        <input className="input !w-64" placeholder="Search node (e.g. P-101, Ramesh)..."
          value={search} onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && doSearch()} />
        <button className="btn-gold !py-1.5" onClick={doSearch}>Find</button>
        <div className="flex gap-2 flex-wrap text-xs">
          {Object.entries(NODE_COLORS).map(([type, color]) => (
            <label key={type} className="flex items-center gap-1 cursor-pointer">
              <input type="checkbox" checked={typeFilter.has(type)}
                onChange={() => {
                  const next = new Set(typeFilter);
                  next.has(type) ? next.delete(type) : next.add(type);
                  setTypeFilter(next);
                }} />
              <span style={{ color }}>● {type}</span>
            </label>
          ))}
        </div>
      </div>

      {!!hlSet.size && (
        <div className="absolute top-16 left-3 z-10 glass px-3 py-2 flex items-center gap-3 max-w-md animate-fade-up">
          <span className="status-pill text-[10px]">Evidence</span>
          <span className="text-xs text-amber-300/90 truncate">Highlighting {hlSet.size} nodes behind: “{hl.query}”</span>
          <button className="text-amber-400/70 hover:text-amber-400 text-sm" onClick={() => hl.clear()}>✕</button>
        </div>
      )}

      <ForceGraph3D
        ref={fgRef}
        graphData={graphData}
        backgroundColor="#040507"
        nodeLabel={(n: any) => `${n.label}: ${n.name}`}
        nodeColor={(n: any) => n.highlighted ? "#ffce88" : (hlSet.size ? "#3a3128" : n.color)}
        nodeVal={(n: any) => n.highlighted ? n.val * 2.6 : n.val}
        linkLabel={(l: any) => l.type}
        linkColor={() => "#4a3626"}
        linkOpacity={0.5}
        onNodeClick={(node: any) => {
          setSelectedNode(node);
          fgRef.current?.cameraPosition(
            { x: node.x + 50, y: node.y + 50, z: node.z + 50 }, node, 1200);
        }}
      />

      {selectedNode && (
        <div className="absolute top-16 right-3 w-80 card z-10 max-h-[75vh] overflow-y-auto">
          <div className="flex justify-between items-center mb-2">
            <span className="badge" style={{ background: selectedNode.color + "33", color: selectedNode.color }}>
              {selectedNode.label}
            </span>
            <button onClick={() => setSelectedNode(null)} className="text-slate-400 text-xl">×</button>
          </div>
          <h3 className="font-bold text-gold-400 mb-2">{selectedNode.name}</h3>
          <dl className="text-xs space-y-1">
            {Object.entries(selectedNode.props || {}).map(([k, v]) => (
              <div key={k} className="grid grid-cols-3 gap-1">
                <dt className="text-slate-500">{k}</dt>
                <dd className="col-span-2 text-slate-300 break-words">{String(v)}</dd>
              </div>
            ))}
          </dl>
          {selectedNode.label === "Equipment" && (
            <a href={`/maintenance?tag=${selectedNode.name}`} className="btn-gold block text-center mt-3 text-sm">
              Open 360° view
            </a>
          )}
        </div>
      )}
    </div>
  );
}
