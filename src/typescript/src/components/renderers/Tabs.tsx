import { useState } from 'react';

export interface TabItem {
  label: string;
  count?: number;
  content: React.ReactNode;
}

interface TabsProps {
  tabs: TabItem[];
}

export default function Tabs({ tabs }: TabsProps) {
  const visibleTabs = tabs.filter(t => t.content != null);
  const [active, setActive] = useState(0);

  if (visibleTabs.length === 0) return null;

  return (
    <div className="r-tabs">
      <div className="r-tab-bar">
        {visibleTabs.map((tab, i) => (
          <button
            key={i}
            className={`r-tab-btn ${i === active ? 'r-tab-active' : ''}`}
            onClick={() => setActive(i)}
          >
            {tab.label}
            {tab.count != null && tab.count > 0 && (
              <span className="r-tab-count">{tab.count}</span>
            )}
          </button>
        ))}
      </div>
      <div className="r-tab-content">
        {visibleTabs[active]?.content}
      </div>
    </div>
  );
}
