import { useEffect, useRef, useState } from "react";

export function projectName(path: string): string {
  const parts = path.split(/[\\/]/).filter(Boolean);
  return parts[parts.length - 1] ?? path;
}

interface RecentProjectListProps {
  projects: string[];
  current: string;
  busy: boolean;
  onOpen: (path: string) => void;
  onForget: (path: string) => void;
}

export function RecentProjectList({ projects, current, busy, onOpen, onForget }: RecentProjectListProps) {
  if (projects.length === 0) return <p className="muted">開いたプロジェクトがここに表示されます。</p>;
  return (
    <nav className="recent-list" aria-label="最近使ったプロジェクト">
      {projects.map((path) => (
        <div className={`recent-item${path === current ? " active" : ""}`} key={path}>
          <button className="recent-project" onClick={() => onOpen(path)} disabled={busy} title={path}>
            <span>{projectName(path)}</span>
            <small>{path}</small>
          </button>
          <button
            className="recent-remove"
            onClick={() => onForget(path)}
            disabled={busy}
            aria-label={`${projectName(path)}を最近使った一覧から削除`}
            title="一覧から削除"
          >
            ×
          </button>
        </div>
      ))}
    </nav>
  );
}

interface ProjectMenuProps extends RecentProjectListProps {
  onChoose: () => void;
}

export default function ProjectMenu({ projects, current, busy, onOpen, onForget, onChoose }: ProjectMenuProps) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return undefined;
    const close = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  return (
    <div className="project-menu" ref={root}>
      <button
        className="project-switcher"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-label="プロジェクトを切り替え"
        title={current}
      >
        <span>{current ? projectName(current) : "プロジェクト未選択"}</span>
        <span aria-hidden="true">▾</span>
      </button>
      {open && (
        <div className="project-menu-popover">
          <RecentProjectList
            projects={projects}
            current={current}
            busy={busy}
            onOpen={(path) => {
              setOpen(false);
              onOpen(path);
            }}
            onForget={onForget}
          />
          <button
            className="button secondary"
            onClick={() => {
              setOpen(false);
              onChoose();
            }}
            disabled={busy}
          >
            フォルダを開く…
          </button>
        </div>
      )}
    </div>
  );
}
