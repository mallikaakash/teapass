"use client";

import { useEffect, useState } from "react";
import { PageView } from "@/components/page/PageView";
import { LOOKS } from "@/lib/looks";
import { PICKER_LOOKS } from "@/lib/schema";
import type { PageState } from "@/lib/page-ops";
import { useStudio } from "./store";
import styles from "./studio.module.css";

export function Studio({ initial }: { initial: PageState }) {
  const studio = useStudio();
  const [paste, setPaste] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    useStudio.getState().load(initial);
  }, [initial.username, initial.version]);

  async function save(publishNow = false) {
    const { draft, baseVersion } = studio.snapshot();
    const response = await fetch("/api/page", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ draft, baseVersion, publish: publishNow }),
    });
    if (response.status === 409) {
      setStatus("Another edit landed. Reload the studio.");
      return;
    }
    if (!response.ok) {
      setStatus("Save failed.");
      return;
    }
    const body = await response.json();
    studio.load(body);
    setStatus(publishNow ? "Published." : "Draft saved.");
  }

  return (
    <div className={styles.shell}>
      <aside className={styles.panel}>
        <h1>Studio</h1>
        <p className={styles.hint}>@{studio.username}</p>
        <label className={styles.field}>
          Garden name
          <input value={studio.page.profile.name} onChange={(e) => studio.updateProfile({ name: e.target.value })} />
        </label>
        <label className={styles.field}>
          Bio
          <textarea value={studio.page.profile.bio} onChange={(e) => studio.updateProfile({ bio: e.target.value })} rows={3} />
        </label>
        <label className={styles.field}>
          Look
          <select value={studio.page.theme.look} onChange={(e) => studio.updateTheme({ look: e.target.value })}>
            {PICKER_LOOKS.map((id) => (
              <option key={id} value={id}>{LOOKS[id].label}</option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          Layout
          <select value={studio.page.theme.layout} onChange={(e) => studio.updateTheme({ layout: e.target.value as "bento" | "list" | "canvas" })}>
            <option value="bento">Bento</option>
            <option value="list">List</option>
            <option value="canvas">Canvas</option>
          </select>
        </label>
        <form
          className={styles.paste}
          onSubmit={(e) => {
            e.preventDefault();
            if (!paste.trim()) return;
            studio.paste(paste);
            setPaste("");
          }}
        >
          <input value={paste} onChange={(e) => setPaste(e.target.value)} placeholder="Paste a link, email, repo…" />
          <button type="submit">Add tile</button>
        </form>
        <div className={styles.actions}>
          <button type="button" onClick={() => studio.undo()}>Undo</button>
          <button type="button" onClick={() => studio.redo()}>Redo</button>
          <button type="button" onClick={() => save(false)}>Save draft</button>
          <button type="button" className={styles.primary} onClick={() => save(true)}>Publish</button>
        </div>
        {status ? <p className={styles.status}>{status}</p> : null}
        <ul className={styles.tiles}>
          {studio.page.tiles.map((tile, index) => (
            <li key={tile.id}>
              <button type="button" onClick={() => studio.select(tile.id)}>{tile.type}</button>
              <button type="button" aria-label="Move up" disabled={index === 0} onClick={() => studio.reorder(index, index - 1)}>↑</button>
              <button type="button" aria-label="Move down" disabled={index === studio.page.tiles.length - 1} onClick={() => studio.reorder(index, index + 1)}>↓</button>
              <button type="button" aria-label="Remove" onClick={() => studio.remove(tile.id)}>×</button>
            </li>
          ))}
        </ul>
      </aside>
      <div className={styles.preview}>
        <PageView page={studio.page} username={studio.username} />
      </div>
    </div>
  );
}
