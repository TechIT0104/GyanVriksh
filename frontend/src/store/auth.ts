import { create } from "zustand";

interface AuthState {
  token: string | null;
  role: string | null;
  name: string | null;
  login: (token: string, role: string, name: string) => void;
  logout: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  token: sessionStorage.getItem("gv_token"),
  role: sessionStorage.getItem("gv_role"),
  name: sessionStorage.getItem("gv_name"),
  login: (token, role, name) => {
    sessionStorage.setItem("gv_token", token);
    sessionStorage.setItem("gv_role", role);
    sessionStorage.setItem("gv_name", name);
    set({ token, role, name });
  },
  logout: () => {
    sessionStorage.clear();
    set({ token: null, role: null, name: null });
  },
}));
