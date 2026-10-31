import { useEffect, useId, useRef, useState } from "react";
import { normalizeCliError, runSprout, type ProjectLabel } from "../lib/sprout";

interface Props {
  projectDir: string;
  program: string;
  leafId: string;
  labels: string[];
  busy: boolean;
  onAdd: (leafId: string, label: string) => Promise<boolean>;
}

const normalized = (label: string) => label.trim().normalize("NFC");

/** Mounted separately for each project/leaf, so candidates and unfinished requests never cross contexts. */
export default function LabelInput({ projectDir, program, leafId, labels, busy, onAdd }: Props) {
  const [draft, setDraft] = useState("");
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<ProjectLabel[]>([]);
  const [state, setState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [error, setError] = useState("");
  const [active, setActive] = useState(-1);
  const [saving, setSaving] = useState(false);
  const request = useRef(0);
  const mounted = useRef(true);
  const pending = useRef(false);
  const root = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const listId = useId();
  const attached = (label: string) => labels.some((item) => normalized(item) === normalized(label));
  const matches = items.filter((item) => item.name.includes(normalized(draft)));
  const selectable = matches.filter((item) => !attached(item.name));

  useEffect(() => { mounted.current = true; return () => { mounted.current = false; request.current += 1; }; }, []);
  useEffect(() => {
    request.current += 1;
    setState("idle");
    setItems([]);
    setOpen(false);
    setActive(-1);
  }, [labels, busy]);
  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false); };
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, [open]);
  useEffect(() => {
    const selected = selectable[active];
    if (open && selected) document.getElementById(`${listId}-${items.indexOf(selected)}`)?.scrollIntoView?.({ block: "nearest" });
  }, [active, open, draft, items]);

  async function load() {
    const current = ++request.current;
    setState("loading");
    setActive(-1);
    try {
      const values = await runSprout<ProjectLabel[]>(projectDir, ["leaf", "label", "list"], program);
      if (!mounted.current || current !== request.current) return;
      if (!Array.isArray(values) || values.some((item) => typeof item.name !== "string" || !Number.isInteger(item.leaf_count))) throw new Error("ラベル一覧を読み取れませんでした");
      setItems(values);
      setState("ready");
    } catch (failure) {
      if (!mounted.current || current !== request.current) return;
      setError(normalizeCliError(failure).message);
      setState("error");
    }
  }

  function show() {
    if (busy || saving) return;
    setOpen(true);
    if (!open) void load();
  }

  async function add(value: string) {
    if (busy || pending.current || !normalized(value) || attached(value)) return;
    pending.current = true;
    setSaving(true);
    setOpen(false);
    try {
      const saved = await onAdd(leafId, value);
      if (saved && mounted.current) setDraft("");
    } finally {
      pending.current = false;
      if (mounted.current) setSaving(false);
    }
  }

  return <div ref={root} className="label-input" onBlur={(event) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false);
  }} onKeyDown={(event) => {
    if (event.key === "Escape" && open) {
      event.preventDefault(); event.stopPropagation(); setOpen(false); setActive(-1); input.current?.focus();
    }
  }}>
    <form className="inline-form" onSubmit={(event) => { event.preventDefault(); void add(draft); }}>
      <input ref={input} role="combobox" aria-label="追加するラベル" aria-autocomplete="list" aria-expanded={open && !busy}
        aria-controls={open ? listId : undefined} aria-activedescendant={open && selectable[active] ? `${listId}-${items.indexOf(selectable[active])}` : undefined}
        placeholder="例: 承認済み" value={draft} disabled={busy || saving} onFocus={show} onClick={show}
        onChange={(event) => { setDraft(event.currentTarget.value); setActive(-1); show(); }} onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            if (!open) { show(); return; }
            if (selectable.length) setActive((index) => index < 0 ? (event.key === "ArrowDown" ? 0 : selectable.length - 1) : (index + (event.key === "ArrowDown" ? 1 : -1) + selectable.length) % selectable.length);
          } else if (event.key === "Enter" && open && selectable[active]) {
            event.preventDefault(); void add(selectable[active].name);
          }
        }} />
      <button className="button secondary small" type="submit" disabled={busy || saving || !normalized(draft) || attached(draft)}>追加</button>
    </form>
    {open && !busy && <div className="label-candidates">
      {state === "loading" && <p role="status" className="field-hint">ラベル候補を読み込み中…</p>}
      {state === "error" && <><p role="status" className="field-hint">候補を取得できませんでした: {error}。新しいラベルは入力して追加できます。</p><button type="button" className="text-button" onClick={() => void load()}>候補を再取得</button></>}
      <div id={listId} role="listbox" aria-label="既存のラベル候補" aria-busy={state === "loading"}>
        {state === "ready" && matches.map((item) => <button type="button" role="option" id={`${listId}-${items.indexOf(item)}`} key={item.name}
          aria-selected={selectable[active]?.name === item.name} disabled={attached(item.name) || saving} onMouseDown={(event) => event.preventDefault()}
          onClick={() => void add(item.name)}>{item.name} <span>{item.leaf_count}件の葉{attached(item.name) ? "・追加済み" : ""}</span></button>)}
      </div>
      {state === "ready" && !matches.length && <p className="field-hint">{items.length ? "一致する候補はありません。新しいラベルを追加できます。" : "使用中のラベルはありません。新しいラベルを追加できます。"}</p>}
    </div>}
  </div>;
}
