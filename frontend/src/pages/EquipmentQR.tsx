import { useQuery } from "@tanstack/react-query";
import { QRCodeSVG } from "qrcode.react";
import { get } from "../api/client";
import PageHeader from "../components/shared/PageHeader";

/** Printable QR stickers, one per equipment. Stick them on the machine; a
 *  technician scans with any phone to open that equipment's view and ask
 *  GyanVriksh hands-free — no typing, no login hunting. */
export default function EquipmentQR() {
  const { data: queue } = useQuery({
    queryKey: ["health-queue"], queryFn: () => get("/maintenance/health-queue"), retry: false,
  });
  const origin = typeof window !== "undefined" ? window.location.origin : "";

  return (
    <div className="p-6">
      <PageHeader icon="qr" kicker="Field Access"
        title="Equipment QR Codes"
        subtitle="Print and stick on machines — scan to open that equipment instantly, hands-free"
        right={<button className="btn-gold print:hidden" onClick={() => window.print()}>Print stickers</button>} />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {(queue ?? []).map((e: any) => {
          const url = `${origin}/mobile?tag=${e.tag_id}`;
          return (
            <div key={e.tag_id} className="paper p-4 flex flex-col items-center text-center">
              <QRCodeSVG value={url} size={132} fgColor="#1a130c" bgColor="#EFE7D7" level="M" marginSize={2} />
              <div className="mono font-bold text-[#1a130c] mt-2 text-lg">{e.tag_id}</div>
              <div className="mono text-[10px] text-[#6b4a2e] uppercase tracking-wide">Scan to ask GyanVriksh</div>
            </div>
          );
        })}
        {!queue?.length && (
          <div className="text-slate-500 col-span-full">Load demo data to generate equipment QR codes.</div>
        )}
      </div>
    </div>
  );
}
