import type { BranchInfo, CommitGraph, GraphCommit, GraphTag } from "./sprout";

export interface CommitTreeRow {
  commit: GraphCommit;
  depth: number;
  hasChildren: boolean;
  branchTips: BranchInfo[];
  tags: GraphTag[];
  currentTip: boolean;
}

export interface FlattenedCommitTree {
  rows: CommitTreeRow[];
  totalVisible: number;
}

function byCreatedAt(left: GraphCommit, right: GraphCommit): number {
  return left.created_at.localeCompare(right.created_at) || left.id.localeCompare(right.id);
}

export function flattenCommitGraph(
  graph: CommitGraph,
  collapsed: ReadonlySet<string>,
  limit: number,
): FlattenedCommitTree {
  const commitsById = new Map(graph.commits.map((commit) => [commit.id, commit]));
  const children = new Map<string, GraphCommit[]>();
  const roots: GraphCommit[] = [];

  for (const commit of graph.commits) {
    if (!commit.parent_id || commit.parent_id === commit.id || !commitsById.has(commit.parent_id)) {
      roots.push(commit);
      continue;
    }
    const siblings = children.get(commit.parent_id) ?? [];
    siblings.push(commit);
    children.set(commit.parent_id, siblings);
  }
  roots.sort(byCreatedAt);
  for (const siblings of children.values()) siblings.sort(byCreatedAt);

  const branchesByCommit = new Map<string, BranchInfo[]>();
  for (const branch of graph.branches) {
    if (!branch.commit_id) continue;
    const values = branchesByCommit.get(branch.commit_id) ?? [];
    values.push(branch);
    branchesByCommit.set(branch.commit_id, values);
  }
  const tagsByCommit = new Map<string, GraphTag[]>();
  for (const tag of graph.tags) {
    const values = tagsByCommit.get(tag.commit_id) ?? [];
    values.push(tag);
    tagsByCommit.set(tag.commit_id, values);
  }

  const rows: CommitTreeRow[] = [];
  const visited = new Set<string>();
  const appendTree = (root: GraphCommit) => {
    const stack: Array<{ commit: GraphCommit; depth: number }> = [{ commit: root, depth: 0 }];
    while (stack.length) {
      const item = stack.pop();
      if (!item || visited.has(item.commit.id)) continue;
      visited.add(item.commit.id);
      const nested = children.get(item.commit.id) ?? [];
      const branchTips = branchesByCommit.get(item.commit.id) ?? [];
      rows.push({
        commit: item.commit,
        depth: item.depth,
        hasChildren: nested.length > 0,
        branchTips,
        tags: tagsByCommit.get(item.commit.id) ?? [],
        currentTip: branchTips.some((branch) => branch.current),
      });
      if (collapsed.has(item.commit.id)) {
        const hidden = [...nested];
        while (hidden.length) {
          const descendant = hidden.pop();
          if (!descendant || visited.has(descendant.id)) continue;
          visited.add(descendant.id);
          hidden.push(...(children.get(descendant.id) ?? []));
        }
        continue;
      }
      for (let index = nested.length - 1; index >= 0; index -= 1) {
        stack.push({ commit: nested[index], depth: item.depth + 1 });
      }
    }
  };

  for (const root of roots) appendTree(root);
  for (const commit of [...graph.commits].sort(byCreatedAt)) {
    if (!visited.has(commit.id)) appendTree(commit);
  }

  const safeLimit = Math.max(1, limit);
  return { rows: rows.slice(0, safeLimit), totalVisible: rows.length };
}
