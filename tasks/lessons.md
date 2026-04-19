# Lessons Learned

## resolveObject() is a flatten tool — never reuse it for hierarchical output

`resolveObject()` intentionally expands all address groups to a flat leaf list.
It is the right tool for search/match scenarios where you only need values.

For any output that must preserve tree structure (copy text, tree rendering),
write a dedicated recursive walker that walks `groups[name]` directly:

```js
const walk = (name, depth, seen) => {
  if (depth > 12 || seen.has(name)) return;
  const members = groups[name];
  if (!members) {
    // leaf address
    lines.push('  '.repeat(depth) + name + (val ? '\t' + val : ''));
    return;
  }
  const seen2 = new Set(seen); seen2.add(name);
  members.forEach(m => {
    if (groups[m]) {
      lines.push('  '.repeat(depth) + m);   // emit sub-group name line
      walk(m, depth + 1, seen2);
    } else {
      // leaf member
      lines.push('  '.repeat(depth) + m + (val ? '\t' + val : ''));
    }
  });
};
walk(item, 1, new Set());
```

**Root cause of the bug**: the old code passed `resolveObject()` output through
`.filter(r => r.type !== 'group' ...)`, stripping every intermediate group node
and collapsing all levels to a flat 2-space-indented list.
