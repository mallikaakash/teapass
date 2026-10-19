"use client";

import { create } from "zustand";
import { addTiles, moveTile, publish, removeTile, setProfile, setTheme, type PageState } from "@/lib/page-ops";
import type { PageDocument } from "@/lib/schema";

type StudioState = {
  serverVersion: number;
  page: PageDocument;
  username: string;
  history: PageDocument[];
  future: PageDocument[];
  selectedId: string | null;
  load: (state: PageState) => void;
  paste: (raw: string) => void;
  reorder: (from: number, to: number) => void;
  remove: (id: string) => void;
  select: (id: string | null) => void;
  updateProfile: (patch: Partial<PageDocument["profile"]>) => void;
  updateTheme: (patch: Partial<PageDocument["theme"]>) => void;
  undo: () => void;
  redo: () => void;
  publishLocal: () => PageDocument;
  snapshot: () => { draft: PageDocument; baseVersion: number };
};

function pushHistory(state: StudioState, next: PageDocument) {
  return {
    page: next,
    history: [...state.history.slice(-99), state.page],
    future: [],
  };
}

export const useStudio = create<StudioState>((set, get) => ({
  serverVersion: 1,
  page: {
    version: 2,
    profile: { name: "", bio: "" },
    theme: { look: "estate", layout: "bento", preset: "mist", font: "fraunces", motion: true, ambient: true },
    tiles: [],
    badge: true,
  },
  username: "",
  history: [],
  future: [],
  selectedId: null,
  load: (state) =>
    set({
      serverVersion: state.version,
      page: state.draft,
      username: state.username,
      history: [],
      future: [],
      selectedId: null,
    }),
  paste: (raw) =>
    set((state) => {
      const next = addTiles({ username: state.username, draft: state.page, published: null, version: state.serverVersion }, raw).draft;
      return pushHistory(state, next);
    }),
  reorder: (from, to) =>
    set((state) => {
      const next = moveTile({ username: state.username, draft: state.page, published: null, version: state.serverVersion }, from, to).draft;
      return pushHistory(state, next);
    }),
  remove: (id) =>
    set((state) => {
      const next = removeTile({ username: state.username, draft: state.page, published: null, version: state.serverVersion }, id).draft;
      return pushHistory(state, next);
    }),
  select: (id) => set({ selectedId: id }),
  updateProfile: (patch) =>
    set((state) => {
      const next = setProfile({ username: state.username, draft: state.page, published: null, version: state.serverVersion }, patch).draft;
      return pushHistory(state, next);
    }),
  updateTheme: (patch) =>
    set((state) => {
      const next = setTheme({ username: state.username, draft: state.page, published: null, version: state.serverVersion }, patch).draft;
      return pushHistory(state, next);
    }),
  undo: () =>
    set((state) => {
      const previous = state.history.at(-1);
      if (!previous) return state;
      return { page: previous, history: state.history.slice(0, -1), future: [state.page, ...state.future] };
    }),
  redo: () =>
    set((state) => {
      const next = state.future[0];
      if (!next) return state;
      return { page: next, history: [...state.history, state.page], future: state.future.slice(1) };
    }),
  publishLocal: () => {
    const state = get();
    return publish({ username: state.username, draft: state.page, published: state.page, version: state.serverVersion }).draft;
  },
  snapshot: () => ({ draft: get().page, baseVersion: get().serverVersion }),
}));
