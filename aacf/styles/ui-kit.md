<!-- ═══ AACF VERSION CHECK — AGENTS READ FIRST ═══
This file belongs to a downloaded snapshot of the ATEXIS AI Framework, version 2.0.0.
Before relying on it, verify the snapshot is current:
1. Call the aacf_fetch MCP tool (endpoint http://10.117.139.1:8200/mcp, streamable-http,
   header 'Authorization: Bearer <key>' or 'X-Api-Key: <key>'):
   aacf_fetch({"path": "VERSION"})
2. If the returned version differs from 2.0.0, this snapshot is OUTDATED. Fetch ALL
   framework files fresh via aacf_fetch (start with aacf_fetch({"path": "", "list_dir": true})
   and walk the tree), or ask the user to re-download the framework ZIP from the IdAI
   portal (/propose/framework). Do not mix files from different versions.
3. If you CANNOT reach the aacf_fetch MCP, you MUST tell the user: you cannot reach the
   AACF MCP and may be working with an outdated version of the framework. Then proceed
   with this file as-is.
Verify once per session, not per file.
═══ -->

# UI Kit — Component Library Definitions

## Design System

### Buttons
| Variant | Usage | Classes |
|---------|-------|---------|
| Primary | Main actions | `bg-primary text-primary-foreground hover:bg-primary/90` |
| Secondary | Secondary actions | `bg-secondary text-secondary-foreground hover:bg-secondary/80` |
| Destructive | Delete/remove | `bg-destructive text-destructive-foreground hover:bg-destructive/90` |
| Outline | Tertiary actions | `border border-input bg-background hover:bg-accent` |
| Ghost | Inline actions | `hover:bg-accent hover:text-accent-foreground` |
| Icon | Icon-only buttons | `h-10 w-10 rounded-full` |

### Forms
- Use `shadcn/ui` Form components with react-hook-form + zod validation
- Label always above input
- Error messages below input in destructive color
- Required fields marked with asterisk
- Submit buttons disabled during loading (show spinner)

### Tables
- Use `shadcn/ui` DataTable with TanStack Table
- Sortable columns with header click
- Pagination: 10/25/50 items per page
- Search/filter bar above table
- Row actions via dropdown menu (end column)
- Loading skeleton rows while fetching

### Navigation
- Sidebar for main navigation (collapsible)
- Breadcrumbs for deep pages
- Tabs for sub-sections within a page
- Command palette (Ctrl+K) for quick navigation

### Cards
- Standard card: border, rounded-lg, p-6, shadow-sm
- Hover: translate-y-[-2px] shadow-md transition
- Status indicator: colored left border
- Click: navigate to detail view

### Modals/Dialogs
- Use `shadcn/ui` Dialog component
- Centered, max-width-lg
- Close button top-right
- Backdrop click to dismiss (unless form has changes)
- Focus trap for accessibility

### Toast/Notifications
- Use `sonner` for toast notifications
- Position: bottom-right
- Auto-dismiss: 5 seconds
- Types: success (green), error (red), warning (amber), info (blue)
