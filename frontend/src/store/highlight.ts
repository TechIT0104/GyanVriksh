import { create } from "zustand";

/** Node names/ids (equipment tags, doc/capsule ids) to light up in the 3D
 *  knowledge graph — set by the Copilot after each answer. */
interface HighlightState {
  nodes: string[];
  query: string;
  set: (nodes: string[], query?: string) => void;
  clear: () => void;
}

export const useHighlight = create<HighlightState>((set) => ({
  nodes: [],
  query: "",
  set: (nodes, query = "") => set({ nodes, query }),
  clear: () => set({ nodes: [], query: "" }),
}));
