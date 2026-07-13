import { create } from "zustand";

/** Tracks whether the user has seen the welcome tour. Persisted in localStorage
 *  so it only auto-plays on first login, but replayable from the sidebar. */
interface TourState {
  toured: boolean;
  finish: () => void;
  replay: () => void;
}

export const useTour = create<TourState>((set) => ({
  toured: localStorage.getItem("gv_toured") === "1",
  finish: () => {
    localStorage.setItem("gv_toured", "1");
    set({ toured: true });
  },
  replay: () => set({ toured: false }),
}));
