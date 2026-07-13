import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { del, get, post, wsUrl } from "../api/client";
import EntityBadge from "../components/shared/EntityBadge";
import PageHeader from "../components/shared/PageHeader";

const STATUS_COLORS: Record<string, string> = {
  QUEUED: "bg-slate-700 text-slate-300", OCR: "bg-blue-900 text-blue-300",
  OCR_DONE: "bg-blue-900 text-blue-300", NER: "bg-purple-900 text-purple-300",
  NER_DONE: "bg-purple-900 text-purple-300", EMBEDDING: "bg-cyan-900 text-cyan-300",
  INDEXED: "bg-emerald-900 text-emerald-300", ERROR: "bg-red-900 text-red-300",
};

export default function Documents() {
  const qc = useQueryClient();
  const [docType, setDocType] = useState("UNKNOWN");
  const [liveStatus, setLiveStatus] = useState<Record<string, string>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: docs } = useQuery({
    queryKey: ["documents"], queryFn: () => get("/documents/"),
    refetchInterval: 5000, retry: false,
  });
  const { data: detail } = useQuery({
    queryKey: ["doc", selected], queryFn: () => get(`/documents/${selected}`),
    enabled: !!selected, retry: false,
  });

  async function upload(files: FileList | null) {
    if (!files) return;
    for (const file of Array.from(files)) {
      const form = new FormData();
      form.append("file", file);
      const res = await post(`/documents/upload?doc_type=${docType}`, form);
      const ws = new WebSocket(wsUrl(`/ws/documents/${res.file_id}/status`));
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.status) {
          setLiveStatus((s) => ({ ...s, [msg.file_id]: `${msg.status} — ${msg.detail}` }));
          if (["INDEXED", "ERROR"].includes(msg.status)) {
            ws.close();
            qc.invalidateQueries({ queryKey: ["documents"] });
          }
        }
      };
    }
    qc.invalidateQueries({ queryKey: ["documents"] });
  }

  return (
    <div className="p-6">
      <PageHeader icon="documents" kicker="Ingestion Pipeline"
        title="Document Management"
        subtitle="Upload, OCR, entity-extract and index plant documents" />

      <div className="card mb-4 border-dashed border-2 !border-navy-600 text-center py-8 cursor-pointer hover:!border-gold-500"
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); upload(e.dataTransfer.files); }}>
        <input ref={fileRef} type="file" multiple hidden
          accept=".pdf,.docx,.xlsx,.jpg,.jpeg,.png,.txt,.md"
          onChange={(e) => upload(e.target.files)} />
        <div className="text-3xl mb-2">📄</div>
        <div className="font-medium">Drop documents here or click to upload</div>
        <div className="text-xs text-slate-400 mt-1">PDF (digital/scanned) · DOCX · XLSX · Images · TXT</div>
        <select className="input !w-auto mt-3 mx-auto" value={docType}
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => setDocType(e.target.value)}>
          {["UNKNOWN", "SOP", "MAINTENANCE_REPORT", "REGULATION", "INCIDENT_REPORT", "INSPECTION_RECORD", "AUDIT_REPORT"]
            .map((t) => <option key={t}>{t}</option>)}
        </select>
      </div>

      <table className="w-full text-sm">
        <thead className="text-left text-slate-400 border-b border-navy-600">
          <tr>
            <th className="py-2">Name</th><th>Type</th><th>Status</th>
            <th>Chunks</th><th>Entities</th><th></th>
          </tr>
        </thead>
        <tbody>
          {(docs ?? []).map((d: any) => (
            <tr key={d.file_id} className="border-b border-navy-700 hover:bg-navy-800 cursor-pointer"
              onClick={() => setSelected(d.file_id)}>
              <td className="py-2">{d.original_name}</td>
              <td className="text-slate-400">{d.doc_type}</td>
              <td>
                <span className={`badge ${STATUS_COLORS[d.status] || ""}`}>{d.status}</span>
                <div className="text-xs text-slate-500">{liveStatus[d.file_id] || d.status_detail}</div>
              </td>
              <td>{d.chunk_count}</td>
              <td>{d.entity_count}</td>
              <td>
                <button className="text-red-400 text-xs hover:underline"
                  onClick={(e) => { e.stopPropagation(); del(`/documents/${d.file_id}`).then(() => qc.invalidateQueries({ queryKey: ["documents"] })); }}>
                  delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {selected && detail && (
        <div className="fixed inset-y-0 right-0 w-[32rem] bg-navy-800 border-l border-navy-600 p-4 overflow-y-auto z-10">
          <div className="flex justify-between items-center mb-3">
            <h2 className="font-semibold text-gold-400">{detail.original_name}</h2>
            <button onClick={() => setSelected(null)} className="text-xl text-slate-400">×</button>
          </div>
          {detail.chunks?.map((c: any) => (
            <div key={c.chunk_id} className="card !p-3 mb-2 text-xs">
              <div className="mb-2 whitespace-pre-wrap text-slate-300">{c.text}</div>
              <div>{c.entities?.map((e: any, i: number) =>
                <EntityBadge key={i} text={e.text} label={e.label} />)}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
