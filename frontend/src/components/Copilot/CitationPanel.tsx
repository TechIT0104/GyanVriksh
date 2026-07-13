import { useQuery } from "@tanstack/react-query";
import { get } from "../../api/client";

export default function CitationPanel({ doc, onClose }:
  { doc: { docId: string; page: number }; onClose: () => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ["doc", doc.docId],
    queryFn: () => get(`/documents/${doc.docId}`),
    retry: false,
  });

  const pageChunks = data?.chunks?.filter((c: any) => c.page === doc.page) ?? data?.chunks ?? [];

  return (
    <div className="w-96 border-l border-navy-600 bg-navy-800 flex flex-col shrink-0">
      <div className="p-3 border-b border-navy-600 flex justify-between items-center">
        <div>
          <div className="font-semibold text-sm text-gold-400">{doc.docId}</div>
          <div className="text-xs text-slate-400">Page {doc.page}</div>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-white text-xl">×</button>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {isLoading && <div className="text-slate-500 text-sm">Loading source...</div>}
        {!isLoading && !pageChunks.length && (
          <div className="text-slate-500 text-sm">
            Source content not available as chunks — this may be a graph record
            (work order / incident / regulation clause).
          </div>
        )}
        {pageChunks.map((c: any) => (
          <div key={c.chunk_id} className="text-xs bg-yellow-500/10 border border-yellow-600/30 rounded p-2 whitespace-pre-wrap">
            {c.text}
          </div>
        ))}
        {data?.download_url && (
          <a href={data.download_url} target="_blank" rel="noreferrer"
            className="btn-ghost block text-center text-sm">Open original file</a>
        )}
      </div>
    </div>
  );
}
