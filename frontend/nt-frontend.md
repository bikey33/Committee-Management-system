# NT Frontend Style & Development Guidelines

Nepal Telecom (NT) frontend coding guidelines, visual standards, design tokens, and component specifications for the React+TypeScript+Tailwind CSS frontend.

---

## 1. Domain & Scope
This applies to all frontend files, including:
- Components (`src/components/**/*.tsx`, `src/components/**/*.ts`)
- Pages (`src/pages/**/*.tsx`)
- Utilities (`src/utils/**/*.ts`, `src/utils/**/*.tsx`)
- Hooks (`src/hooks/**/*.ts`)
- Configs (`tailwind.config.ts`, `postcss.config.js`)

---

## 2. Technology Stack
- **Framework**: React 18 (Vite, TypeScript)
- **Styling**: Tailwind CSS v3 & Tailwind CSS Animate, HSL theme variables
- **Icons**: `lucide-react` exclusively (e.g., `Menu`, `Settings`, `Sun`, `Moon`, `Users`, `LogOut`)
- **Components & Primitives**: Radix UI Primitives (Accordion, Dialog, Popover, Select, etc.), Shadcn UI components, Framer Motion for premium micro-animations
- **State Management & Fetching**: TanStack Query (React Query) v5, Axios for API clients

---

## 3. Light & Dark Theme Design System

Never hardcode static color classes — Tailwind variables must adapt dynamically inside a `.dark` scope.

### A. Design Tokens
| Token Role | Light Mode Value (Root) | Dark Mode Value (`.dark`) | Tailwind class |
|---|---|---|---|
| **Background** | `hsl(0 0% 100%)` | `hsl(224 71% 4%)` | `bg-background` |
| **Foreground** | `hsl(222.2 84% 4.9%)` | `hsl(213 31% 91%)` | `text-foreground` |
| **Primary** | `hsl(209 100% 32%)` (NT Blue) | `hsl(210 40% 98%)` | `bg-primary` / `text-primary` |
| **Primary Hover** | `hsl(209 100% 28%)` (Darker Blue) | `—` | `hover:bg-primary-hover` |
| **Primary Foreground** | `hsl(0 0% 98%)` | `hsl(222.2 47.4% 11.2%)` | `text-primary-foreground` |
| **NT Gold** | `#E6B646` (Brand Gold) | `#E6B646` (Brand Gold) | `text-[#E6B646]` |
| **Secondary** | `hsl(210 40% 96.1%)` | `hsl(222.2 47.4% 11.2%)` | `bg-secondary` |
| **Secondary Foreground** | `hsl(222.2 47.4% 11.2%)` | `hsl(210 40% 98%)` | `text-secondary-foreground` |
| **Muted** | `hsl(210 40% 96.1%)` | `hsl(223 47% 11%)` | `bg-muted` |
| **Muted Foreground** | `hsl(215.4 16.3% 46.9%)` | `hsl(215.4 16.3% 46.9%)` | `text-muted-foreground` |
| **Accent** | `hsl(209 100% 32%)` (NT Blue) | `hsl(216 34% 17%)` | `bg-accent` |
| **Accent Foreground** | `hsl(0 0% 98%)` | `hsl(210 40% 98%)` | `text-accent-foreground` |
| **Destructive** | `hsl(0 84.2% 60.2%)` | `hsl(0 63% 31%)` | `bg-destructive` |
| **Destructive Foreground** | `hsl(210 40% 98%)` | `hsl(210 40% 98%)` | `text-destructive-foreground` |
| **Border / Input** | `hsl(214.3 31.8% 91.4%)` | `hsl(216 34% 17%)` | `border-border` / `border-input` |
| **Ring** | `hsl(209 100% 32%)` | `hsl(216 34% 17%)` | `ring-ring` |

### B. Global Dark Mode Layout Customization
- **Table Headers (`thead`, `th`)**: Light → `bg-primary` with white bold text. Dark → `background-color: hsl(var(--card)) !important` with high-contrast text.
- **Brand Headers (`.brand-header`)**: Light → `background-color: hsl(209 100% 32%)` with white text. Dark → `background-color: hsl(224 71% 4%) !important` with `border-b border-slate-800`.
- **Glassmorphism (`.glass-card`)**: Light → `background: rgba(255,255,255,0.8)` with `backdrop-blur-lg border border-white/20`. Dark → `background: rgba(15,23,42,0.6) !important` with `border: 1px solid rgba(255,255,255,0.1) !important`.
- **Utility Overrides**: `bg-white`, `bg-slate-50`, `text-slate-800`, `border-slate-200` must map to semantic CSS variables inside `.dark` (e.g. `.dark .bg-white { background-color: hsl(var(--card)) !important; }`).

---

## 4. Sidebar Layout & Collapsible Navigation

### A. Sidebar Shell
- `collapsible="icon"`, className: `"border-r border-sidebar-border bg-sidebar text-sidebar-foreground flex-shrink-0 top-[60px] h-[calc(100vh-60px)] z-30 shadow-sm"`
- Light: `--sidebar-background: 0 0% 98%`, `--sidebar-border: 220 13% 91%`
- Dark: `--sidebar-background: 224 71% 4%`, `--sidebar-border: 216 34% 17%`
- Padding — Expanded: `px-4 pt-6 pb-6` / Collapsed: `px-2 pt-6 pb-6`
- Footer: `py-3 border-t border-sidebar-border bg-sidebar`, padding `px-4` (expanded) or `px-1` (collapsed)

### B. Nav Items (`CollapsibleNavItem`)
- Wrapper: `h-auto rounded-md transition-all duration-200 group relative overflow-hidden cursor-pointer`
- Active: `bg-primary/10 text-primary hover:text-primary font-medium`
- Inactive: `text-[hsl(var(--sidebar-foreground))] hover:bg-primary/10 hover:text-primary font-medium`
- Icon wrapper: `relative flex items-center justify-center rounded-lg transition-all duration-200`, size `w-9 h-9` (collapsed) or `w-5 h-5` (expanded)
- Icon: `flex-shrink-0 transition-transform duration-200 h-5 w-5 text-sidebar-foreground` (or `text-primary` if active)
- Label: `whitespace-nowrap truncate text-sm relative z-10 ml-2 flex-1 text-left`, hidden when collapsed

### C. Toggle Trigger
- Icon: **`Menu`** from `lucide-react` only
- Button classes: `text-[hsl(var(--header-foreground))] hover:bg-white/10 group active:scale-95 transition-all`, variant `ghost`, size `icon`
- Rotation: Expanded → `rotate-180`, Collapsed → `rotate-0`, transition: `h-5 w-5 transition-transform duration-300 ease-in-out`

---

## 5. Login Page (Forced Light Mode)

### A. Forced Light Theme Scope (`.forced-light`)
- NT Blue Primary: `--primary: 209 100% 32%` / `--ring: 209 100% 32%`
- Input Borders: `--border: 214.3 31.8% 91.4%`
- Background: `--background: 0 0% 100%`
- Override: `.forced-light .bg-white { background-color: white !important; color: #0f172a !important; }`

### B. Gradient Background (`.gradient-background`)
```css
.gradient-background {
  background: linear-gradient(-45deg,
      hsl(209 100% 32%),
      hsl(209 100% 28%),
      hsl(210 50% 93%),
      hsl(209 100% 28%));
  background-size: 400% 400%;
  animation: gradientShift 15s ease infinite;
}
```

---

## 6. Date Utilities (Bikram Sambat / Nepali Calendar)

Always import from `@/utils/nepaliDate` and `@/utils/dateFormatter`:

- **`formatBS(date)`** — Returns BS date string (e.g., `2080-12-16`). Use in list items, inputs, badges.
- **`formatADBS(date, adFormat?, showTime?)`** — Returns React element: AD bold on top, BS muted below. Use in tables, cards.
- **`formatADBSString(date, adFormat?)`** — Single-line string: `Mar 28, 2026 (2082-12-15)`. Use in PDFs, headers.
- **`formatDateWithSuperscript(dateString)`** — Ordinal suffixes (e.g., `March 28th, 2026`) with BS below. Use in timelines, review panels.

---

## 7. Premium UX & Accessibility

- **Micro-animations**: Use Framer Motion or `animate-in fade-in duration-500` for tabs, cards, list entries.
- **Theme toggle**: Sun/Moon icons rotate and scale smoothly — Sun: `isDark ? "opacity-100 rotate-0 scale-100" : "opacity-0 rotate-90 scale-50"`. Moon: opposite.
- **Transitions**: Always use `transition-all duration-200` or `duration-300`; never instant state changes.
- **Focus states**: `focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2`
- **Responsive**: Test at 375px, 768px, 1024px, 1440px+. No fixed overflow without fallback scrolling.

---

## 8. Code Snippets

### Sidebar Toggle
```tsx
import { Button } from '@/components/ui/button';
import { Menu } from 'lucide-react';
import { cn } from '@/lib/utils';

export const SidebarToggle = ({ isCollapsed, onToggle }) => (
  <Button variant="ghost" size="icon"
    className="text-white hover:bg-white/10 active:scale-95 transition-all"
    onClick={onToggle}>
    <Menu className={cn("h-5 w-5 transition-transform duration-300 ease-in-out",
      isCollapsed ? "" : "rotate-180")} />
  </Button>
);
```

### Theme Toggle
```tsx
import { Button } from '@/components/ui/button';
import { Sun, Moon } from 'lucide-react';
import { cn } from '@/lib/utils';

export const ThemeToggle = ({ isDark, onToggle }) => (
  <Button variant="ghost" size="icon" className="relative overflow-hidden" onClick={onToggle}>
    <span className={cn("absolute inset-0 flex items-center justify-center transition-all duration-300",
      isDark ? "opacity-100 rotate-0 scale-100" : "opacity-0 rotate-90 scale-50")}>
      <Sun className="h-5 w-5" />
    </span>
    <span className={cn("absolute inset-0 flex items-center justify-center transition-all duration-300",
      isDark ? "opacity-0 -rotate-90 scale-50" : "opacity-100 rotate-0 scale-100")}>
      <Moon className="h-5 w-5" />
    </span>
  </Button>
);
```

### Standard Table
```tsx
export const StandardTable = ({ headers, rows }) => (
  <div className="w-full overflow-x-auto rounded-md border border-border">
    <table className="w-full border-collapse text-sm">
      <thead className="bg-primary text-primary-foreground dark:bg-card">
        <tr>{headers.map((h, i) => <th key={i} className="p-4 text-left font-medium">{h}</th>)}</tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i} className="border-b border-border hover:bg-muted/50 transition-colors">
            <td className="p-4 font-semibold text-slate-800 dark:text-foreground">{row.name}</td>
            <td className="p-4">{row.date}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);
```

### Standard Footer
```tsx
export const StandardFooter = ({ appVersion }) => (
  <footer className="border-t bg-background py-4 w-full mt-auto">
    <div className="container mx-auto px-6 flex flex-col items-center justify-center gap-1.5 text-sm text-muted-foreground">
      <p className="text-center font-medium">
        &copy; {new Date().getFullYear()} Procurement Management System - Nepal Telecom. All rights reserved.
      </p>
      <p className="text-xs text-center">
        Developed By: <span className="text-primary font-bold">ITD, Software and Security Wing</span>
      </p>
    </div>
  </footer>
);
```

---

## 9. Strictly Forbidden Anti-patterns

- ❌ **Emojis as icons** — Use Lucide icons exclusively.
- ❌ **Hex colors** — Never hardcode `#0055ff`. Use `bg-primary`, `hsl(var(--primary))`, etc.
- ❌ **Low contrast** — Minimum 4.5:1 contrast ratio always.
- ❌ **Layout-shifting hover scales** — No transforms that shift adjacent DOM elements.
- ❌ **Missing `cursor-pointer`** — All interactive wrappers must have it.
- ❌ **Hardcoded fiscal years** — Use `getCurrentFiscalYear()` or `generateFiscalYears()`.
