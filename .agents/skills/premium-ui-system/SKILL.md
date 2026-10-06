---
name: premium-ui-system
description: >-
  Enforces Figma-grade, anti-AI-slop UI design standards across Web, Desktop (Qt/PyQt),
  and Roblox. Strictly bans raw Unicode emojis as icons, mandates Lucide/SVG vector
  icon sets, physics-based micro-animations (springs, 3D button press, hover lifts),
  rich dark-mode palettes, and tactile feedback.
---

# Premium UI Design System & Engineering Guide

> **MANDATE**: Deliver high-fidelity, polished, responsive UI interfaces that look like
> they were crafted by senior Figma product designers, not generic AI prototypes.

---

## 1. Core Directives

1. **Strictly No Emojis As Icons**:
   - ❌ Never use raw emojis (`🔥`, `🚀`, `⭐`, `⚙️`, `💰`) inside action buttons, tabs, or badges.
   - ✅ Always use Lucide icons, Phosphor, Heroicons, or SVG vector paths.
2. **Tactile Micro-Interactions**:
   - Every interactive element (buttons, cards, toggles) MUST have distinct `hover`, `active/press`, and `focus` animations.
   - Use spring physics or cubic-bezier curves (`cubic-bezier(0.16, 1, 0.3, 1)`).
3. **Layered Visual Depth**:
   - Frosted glassmorphism (`backdrop-filter: blur(16px)`).
   - Multi-layer drop shadows (ambient diffuse + crisp directional).
   - Subtle inner borders (`border: 1px solid rgba(255, 255, 255, 0.08)`).
4. **Deliberate Palette**:
   - Deep canvas (`#090A0F`, `#0E1117`), elevated surfaces (`#161B26`, `#1F2433`).
   - Saturated high-contrast accents (Cyan `#00F0FF`, Violet `#8B5CF6`, Emerald `#10B981`, Amber `#F59E0B`).

---

## 2. Icon Integration Guide (Lucide & Vector)

### Web (React / Tailwind)
```tsx
import { 
  Sparkles, 
  Flame, 
  Settings, 
  ShieldCheck, 
  Coins, 
  Crosshair, 
  ChevronRight,
  X 
} from 'lucide-react';

// Premium Button Example:
export function EliteButton({ children, icon: Icon, onClick, variant = 'primary' }) {
  return (
    <button
      onClick={onClick}
      className={`
        relative group inline-flex items-center gap-2.5 px-5 py-2.5 rounded-xl font-semibold text-sm
        transition-all duration-200 ease-out active:scale-95 active:translate-y-0.5
        shadow-lg hover:shadow-cyan-500/20 hover:-translate-y-0.5
        ${variant === 'primary' 
          ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-cyan-500/10 border border-cyan-400/30' 
          : 'bg-slate-900/80 text-slate-200 hover:text-white border border-white/10 hover:border-white/25'}
      `}
    >
      {Icon && <Icon className="w-4 h-4 transition-transform duration-200 group-hover:scale-110" />}
      <span>{children}</span>
    </button>
  );
}
```

### Desktop (PyQt6 / Qt)
For PyQt6 applications, do not rely on emoji labels:
```python
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtCore import QSize

# Apply clean stylesheet with tactile states
ELITE_BUTTON_STYLE = """
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E2333, stop:1 #131722);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-bottom: 3px solid #0B0E17;
    border-radius: 10px;
    color: #E2E8F0;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 16px;
    min-height: 24px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #282F45, stop:1 #1A1F2E);
    border-color: rgba(0, 240, 255, 0.4);
    color: #FFFFFF;
}
QPushButton:pressed {
    background: #0E121B;
    border-bottom: 1px solid #0B0E17;
    margin-top: 2px;
}
"""
```

---

## 3. Micro-Animation Keyframes (CSS / Web)

```css
/* Tactile spring entrance */
@keyframes modalPopIn {
  0% {
    opacity: 0;
    transform: scale(0.92) translateY(12px);
  }
  70% {
    transform: scale(1.02) translateY(-2px);
  }
  100% {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

/* Shimmer highlight for rare cards / items */
@keyframes borderGlow {
  0%, 100% {
    border-color: rgba(139, 92, 246, 0.4);
    box-shadow: 0 0 15px rgba(139, 92, 246, 0.2);
  }
  50% {
    border-color: rgba(0, 240, 255, 0.7);
    box-shadow: 0 0 25px rgba(0, 240, 255, 0.35);
  }
}

.elite-modal-enter {
  animation: modalPopIn 320ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.glow-card {
  animation: borderGlow 3s ease-in-out infinite;
}
```

---

## 4. Design Review Checklist
Before marking any UI work complete:
- [ ] Are any raw Unicode emojis used as icons? If yes, replace them with SVGs or Lucide icons immediately.
- [ ] Does every button provide distinct visual feedback for hover, active/press, and disabled states?
- [ ] Are animations smooth (easing function used, no jarring abrupt teleportations)?
- [ ] Is contrast compliant (WCAG AA) against dark backgrounds?
- [ ] Is spacing and typography hierarchical and deliberate?
