import { ArrowRight, Clock3, Database, Rows3 } from "lucide-react";
import { UploadDialog } from "@/components/upload-dialog";
import { Button } from "@/components/ui/button";

const recentDatasets = [
  {
    name: "Ecommerce orders",
    description: "Orders, products, customers, and fulfilment details.",
    rows: "12,480 rows",
    columns: "14 columns",
    updated: "Sample data",
  },
];

export function DatasetLibrary() {
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Workspace</p>
          <h1>Your datasets</h1>
          <p className="lede">Upload a source, check its shape and quality, then begin an analysis.</p>
        </div>
        <UploadDialog />
      </div>

      <section className="library-panel" aria-labelledby="recent-heading">
        <div className="section-heading">
          <div>
            <h2 id="recent-heading">Recent datasets</h2>
            <p>Sources available for analysis in this workspace.</p>
          </div>
          <span className="count-label">{recentDatasets.length} dataset</span>
        </div>

        <div className="dataset-list">
          {recentDatasets.map((dataset) => (
            <article className="dataset-row" key={dataset.name}>
              <span className="dataset-glyph"><Database size={19} /></span>
              <div className="dataset-copy">
                <h3>{dataset.name}</h3>
                <p>{dataset.description}</p>
              </div>
              <dl className="dataset-meta">
                <div><Rows3 size={13} /><dt className="sr-only">Rows</dt><dd>{dataset.rows}</dd></div>
                <div><Database size={13} /><dt className="sr-only">Columns</dt><dd>{dataset.columns}</dd></div>
                <div><Clock3 size={13} /><dt className="sr-only">Updated</dt><dd>{dataset.updated}</dd></div>
              </dl>
              <Button variant="ghost" size="small" aria-label={`Open ${dataset.name}`}><ArrowRight size={16} /></Button>
            </article>
          ))}
        </div>
      </section>

      <aside className="sample-callout">
        <div>
          <strong>New to SignalDesk?</strong>
          <p>Open the ecommerce sample to see how profiles and analysis fit together.</p>
        </div>
        <Button variant="secondary" size="small">Explore sample data</Button>
      </aside>
    </>
  );
}
