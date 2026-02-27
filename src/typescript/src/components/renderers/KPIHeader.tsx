import type { KPIItem } from '../../types/schemas';

interface Props {
  summary: string;
  kpis: KPIItem[];
}

export default function KPIHeader({ kpis }: Props) {
  if (kpis.length === 0) return null;

  return (
    <div className="r-kpi-header">
      <div className="r-kpi-row">
        {kpis.map((kpi, i) => (
          <div key={i} className={`r-kpi-item r-kpi-${kpi.color || 'gray'}`}>
            <span className="r-kpi-value">{kpi.value}</span>
            <span className="r-kpi-label">{kpi.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
