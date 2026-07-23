const navigationItems = ["Dashboard", "Projects", "Upload", "Analysis", "Quantities", "Reports"];
const workspacePanels = ["Drawing Viewer", "AI Status", "BOQ"];

export default function Home() {
  return (
    <main className="workspace-shell">
      <aside className="workspace-sidebar" aria-label="Workspace navigation">
        <h1>BitonX Quant</h1>
        <nav>
          {navigationItems.map((item) => (
            <p key={item}>{item}</p>
          ))}
        </nav>
      </aside>
      <section className="workspace-main">
        <header className="workspace-header">
          <div>
            <p>Phase 2</p>
            <h2>Workspace Foundation</h2>
          </div>
          <strong>Ready</strong>
        </header>
        <div className="workspace-grid">
          {workspacePanels.map((panel) => (
            <section className="workspace-panel" key={panel}>
              <h3>{panel}</h3>
            </section>
          ))}
        </div>
      </section>
    </main>
  );
}

