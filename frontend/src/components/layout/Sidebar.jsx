// src/components/layout/Sidebar.jsx
import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Briefcase, Mic,
  ChevronLeft, ChevronRight, Sparkles, Brain,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/",           icon: LayoutDashboard, label: "Dashboard"  },
  { to: "/jobs",       icon: Briefcase,       label: "Jobs"        },
  { to: "/interviews", icon: Mic,             label: "Interviews"  },
  { to: "/softskills", icon: Brain,           label: "Soft Skills" },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside className={cn(
      "h-screen flex flex-col bg-slate-900 border-r border-slate-800 shrink-0 transition-all duration-200",
      collapsed ? "w-15" : "w-55"
    )}>

      {/* Logo */}
      <div className={cn(
        "h-14 flex items-center border-b border-slate-800 px-4 gap-3 shrink-0",
        collapsed && "justify-center px-0"
      )}>
        <div className="w-7 h-7 rounded-lg bg-indigo-500 flex items-center justify-center shrink-0 shadow-lg shadow-indigo-500/30">
          <Sparkles className="w-3.5 h-3.5 text-white" />
        </div>
        {!collapsed && (
          <span className="text-sm font-semibold text-white tracking-tight">AI Analyzer</span>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {!collapsed && (
          <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-600 px-3 mb-2">
            Menu
          </p>
        )}
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) => cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all group relative",
              isActive
                ? "bg-white/10 text-white shadow-sm"
                : "text-slate-400 hover:bg-white/5 hover:text-slate-200",
              collapsed && "justify-center"
            )}
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-indigo-400 rounded-r-full" />
                )}
                <item.icon className={cn(
                  "w-4 h-4 shrink-0 transition-transform group-hover:scale-110",
                  !collapsed && "ml-1"
                )} />
                {!collapsed && <span className="truncate">{item.label}</span>}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Collapse toggle */}
      <div className="p-3 border-t border-slate-800 shrink-0">
        <button
          onClick={() => setCollapsed((c) => !c)}
          className={cn(
            "w-full flex items-center gap-2 px-3 py-2 rounded-xl text-slate-500",
            "hover:bg-white/5 hover:text-slate-300 transition-all text-xs font-medium",
            collapsed && "justify-center"
          )}
        >
          {collapsed
            ? <ChevronRight className="w-4 h-4" />
            : <><ChevronLeft className="w-4 h-4" /><span>Collapse</span></>
          }
        </button>
      </div>
    </aside>
  );
}